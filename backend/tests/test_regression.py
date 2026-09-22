"""Pin every KPI on the real district to two decimals.

Skipped when the warehouse has not been built (`make load-data`), so the suite stays green
on a data-less checkout; with data present, any change in the pipeline, the SQL or the
Overture release shows up as a diff here. Values as of Overture 2026-08-19.0.
"""

from __future__ import annotations

import pytest
from django.conf import settings

from apps.areas.resolve import AreaRequest, resolve
from apps.kpis import definitions, service
from apps.kpis.engine import compute

EXPECTED: dict[str, tuple[float, int]] = {
    # key: (value to 2 dp, sample_size)
    "low_speed_street_share": (50.73, 1435),
    "crossing_density": (22.60, 1754),
    "pedestrian_network_share": (20.6, 3562),  # sidewalks and crosswalks excluded
    "green_space_distance_p50": (362.49, 8397),  # public green classes only
    "street_tree_density": (55.38, 1754),
}

pytestmark = pytest.mark.skipif(
    not settings.WAREHOUSE_PATH.is_file(), reason="warehouse not built (make load-data)"
)


@pytest.mark.django_db
def test_district_kpis_pinned_to_two_decimals() -> None:
    with service.warehouse().cursor() as con:
        area = resolve(con, AreaRequest(district="eixample"), service.district_refs())
        response = compute(con, area, definitions.load().kpis, with_layers=False)
    assert area.district_overlap_share == pytest.approx(1.0, abs=1e-9)
    assert response.area.km2 == pytest.approx(7.508, abs=5e-4)
    assert response.meta.overture_release == "2026-08-19.0"
    actual = {k.key: (round(k.row.value or 0.0, 2), k.row.sample_size) for k in response.kpis}
    assert actual == EXPECTED


@pytest.mark.django_db
def test_polygon_containing_the_district_matches_the_district_to_two_decimals() -> None:
    """The warehouse stores whole geometries of features that touch the district; a bigger
    polygon must not count the parts outside it."""
    kpis = definitions.load().kpis
    with service.warehouse().cursor() as con:
        district = compute(
            con,
            resolve(con, AreaRequest(district="eixample"), service.district_refs()),
            kpis,
            with_layers=False,
        )
        bigger = compute(
            con,
            resolve(con, AreaRequest(bbox=(2.135, 41.370, 2.195, 41.418)), {}),
            kpis,
            with_layers=False,
        )
    assert 0.2 < bigger.area.district_overlap_share < 0.5
    for a, b in zip(district.kpis, bigger.kpis, strict=True):
        assert round(a.row.value or 0, 2) == round(b.row.value or 0, 2), a.key
        assert a.row.sample_size == b.row.sample_size, a.key
