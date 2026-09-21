"""Two requests on the shared connection must never see each other's area.

The area lives in a temp table, a ``SET VARIABLE`` and a temp macro. If cursors did not
isolate those, request B could overwrite request A's polygon and A would get B's numbers with
no error — plausible, wrong values. This test fires two threads at the process-wide handle
with two different polygons, many times, each asserting it got its own numbers back.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from apps.areas.resolve import AreaRequest, resolve
from apps.kpis.registry import SPEC_BY_KEY
from tests.fixtures.synthetic import SyntheticWarehouse, box_wkt_m
from warehouse import area as warehouse_area
from warehouse.connection import Warehouse
from warehouse.kpi import run_kpi

ROUNDS = 100


@pytest.fixture
def path(tmp_path: Path) -> Path:
    """Area A holds a 30 km/h street (share 100); area B a 50 km/h street (share 0)."""
    file = tmp_path / "warehouse.duckdb"
    wh = SyntheticWarehouse(file)
    wh.segment(100, 100, 600, 100, speed=30)
    wh.segment(1_100, 100, 1_600, 100, speed=50)
    wh.close()
    return file


def test_concurrent_requests_keep_their_own_area(path: Path) -> None:
    handle = Warehouse(path)
    helper = SyntheticWarehouse()  # only for the metres -> GeoJSON conversion
    areas = {
        "A": (helper.geojson(box_wkt_m(0, 0, 1_000, 1_000)), 100.0),
        "B": (helper.geojson(box_wkt_m(1_000, 0, 2_000, 1_000)), 0.0),
    }
    barrier = threading.Barrier(len(areas))
    failures: list[str] = []

    def worker(name: str) -> None:
        polygon, expected = areas[name]
        barrier.wait()
        for i in range(ROUNDS):
            with handle.cursor() as con:
                resolved = resolve(con, AreaRequest(polygon=polygon), {})
                warehouse_area.register_area(con, resolved.effective_wkt)
                row = run_kpi(con, SPEC_BY_KEY["low_speed_street_share"].sql)
            if row.value != expected or row.sample_size != 1:
                failures.append(f"{name}#{i}: got {row.value} (n={row.sample_size})")
                return

    threads = [threading.Thread(target=worker, args=(name,)) for name in areas]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not failures, failures
    assert not any(t.is_alive() for t in threads)
