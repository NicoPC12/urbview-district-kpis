"""API contract tests on a synthetic warehouse file: shapes, problem details, cache, reload.

Nothing here needs the real extract. Each test builds a tiny warehouse file in ``tmp_path``
and points ``WAREHOUSE_PATH`` at it, so the process-wide handle, the 503 path and the
rebuild-without-restart path are all exercised the way the running container hits them.
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.areas.models import District
from apps.kpis.models import KpiDefinition
from tests.fixtures.synthetic import X0, Y0, SyntheticWarehouse

PROBLEM_JSON = "application/problem+json"


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def warehouse_path(tmp_path: Path) -> Iterator[Path]:
    """A synthetic warehouse file with one 30 km/h street, one crossing, one tree, one park."""
    path = tmp_path / "warehouse.duckdb"
    wh = SyntheticWarehouse(path)
    wh.segment(100, 100, 600, 100, speed=30, name="Carrer de Prova")
    wh.segment(100, 200, 600, 200, cls="footway")
    wh.crossing(300, 100)
    wh.tree(200, 90)
    wh.building(300, 150)
    wh.green(700, 100, 800, 200)
    wh.close()
    with override_settings(WAREHOUSE_PATH=path):
        yield path


@pytest.fixture
def district(db: None) -> District:
    return District.objects.create(
        slug="test", name="Test district", overture_id=SyntheticWarehouse.DISTRICT_ID
    )


def square(xmin: float, ymin: float, xmax: float, ymax: float) -> dict[str, Any]:
    """A GeoJSON polygon in grid metres, converted the way the fixture does it."""
    wh = SyntheticWarehouse()
    coords = f"{X0 + xmin} {Y0 + ymin}, {X0 + xmax} {Y0 + ymin}, {X0 + xmax} {Y0 + ymax}, "
    coords += f"{X0 + xmin} {Y0 + ymax}, {X0 + xmin} {Y0 + ymin}"
    return wh.geojson(f"POLYGON(({coords}))")


def bbox_of(polygon: dict[str, Any]) -> list[float]:
    ring = polygon["coordinates"][0]
    return [
        min(p[0] for p in ring),
        min(p[1] for p in ring),
        max(p[0] for p in ring),
        max(p[1] for p in ring),
    ]


def post(client: APIClient, body: dict[str, Any]) -> Any:
    return client.post("/api/v1/kpis", body, format="json")


# --- shapes ------------------------------------------------------------------------------


@pytest.mark.django_db
def test_all_three_request_forms_return_the_same_shape(
    client: APIClient, warehouse_path: Path, district: District
) -> None:
    polygon = square(0, 0, 1_000, 1_000)
    responses = {
        "district": post(client, {"district": "test"}),
        "bbox": post(client, {"bbox": bbox_of(polygon)}),
        "polygon": post(client, {"polygon": polygon}),
    }
    bodies = {k: r.json() for k, r in responses.items()}
    for kind, r in responses.items():
        assert r.status_code == 200, (kind, r.content[:200])
        assert r["Content-Type"] == "application/json"
        assert set(bodies[kind]) == {"area", "kpis", "insights", "legend", "layers", "meta"}
        assert bodies[kind]["area"]["source"] == {"polygon": "drawn"}.get(kind, kind)
        assert [k["key"] for k in bodies[kind]["kpis"]] == [
            "low_speed_street_share",
            "crossing_density",
            "pedestrian_network_share",
            "green_space_distance_p50",
            "street_tree_density",
        ]
    # The bbox and the polygon are the same square: identical numbers, identical layers.
    assert bodies["bbox"]["kpis"] == bodies["polygon"]["kpis"]
    assert bodies["bbox"]["layers"] == bodies["polygon"]["layers"]
    # The district (2 km square) contains the same features: same values, larger area.
    assert bodies["district"]["area"]["district_overlap_share"] == 1.0
    assert bodies["district"]["area"]["km2"] == pytest.approx(4.0, abs=1e-3)
    low_speed = bodies["polygon"]["kpis"][0]
    assert low_speed["value"] == 100.0
    assert low_speed["band"] == "Calmed"
    assert low_speed["source"]["kind"] == "citation"
    assert "breakdown" in low_speed and "breakdown_note" not in low_speed
    assert "breakdown" not in bodies["polygon"]["kpis"][1]  # crossings: deliberately none
    assert bodies["polygon"]["kpis"][1]["breakdown_note"].startswith("No breakdown")


@pytest.mark.django_db
def test_layer_features_carry_only_what_the_frontend_reads(
    client: APIClient, warehouse_path: Path
) -> None:
    body = post(client, {"polygon": square(0, 0, 1_000, 1_000)}).json()
    layers = {layer["id"]: layer for layer in body["layers"]["vectors"]}
    street = layers["streets_speed"]["data"]["features"][0]
    assert street["id"].startswith("seg-")
    assert street["properties"] == {
        "category": "le30",
        "name": "Carrer de Prova",
        "length_m": 500.0,
    }
    footway = layers["streets_class"]["data"]["features"]
    assert {f["properties"]["category"] for f in footway} == {"residential", "footway"}
    assert (
        "name"
        not in next(f for f in footway if f["properties"]["category"] == "footway")["properties"]
    )
    assert layers["crossings"]["data"]["features"][0]["properties"] == {"category": "crossing"}
    lon, lat = layers["trees"]["data"]["features"][0]["geometry"]["coordinates"]
    assert len(str(lon).split(".")[1]) <= 5 and len(str(lat).split(".")[1]) <= 5


# --- outside and across the district boundary --------------------------------------------


@pytest.mark.django_db
def test_polygon_outside_the_district_is_200_and_empty(
    client: APIClient, warehouse_path: Path
) -> None:
    response = post(client, {"polygon": square(5_000, 5_000, 5_500, 5_500)})
    assert response.status_code == 200
    body = response.json()
    assert body["area"]["district_overlap_share"] == 0.0
    assert all(k["value"] is None and k["sample_size"] == 0 for k in body["kpis"])
    assert all(k["band"] is None for k in body["kpis"])
    assert all(layer["data"]["features"] == [] for layer in body["layers"]["vectors"])
    assert "none of the features" in body["insights"][0]


@pytest.mark.django_db
def test_polygon_crossing_the_boundary_reports_the_share_with_data(
    client: APIClient, warehouse_path: Path
) -> None:
    body = post(client, {"polygon": square(1_000, 0, 3_000, 1_000)}).json()  # half inside
    assert body["area"]["district_overlap_share"] == pytest.approx(0.5, abs=1e-6)
    assert any("50% of this" in s and "inside the loaded district" in s for s in body["insights"])


# --- 422 problem details -----------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("body", "title", "hint"),
    [
        (
            {
                "polygon": {
                    "type": "Polygon",
                    "coordinates": [
                        [[2.16, 41.39], [2.17, 41.40], [2.17, 41.39], [2.16, 41.40], [2.16, 41.39]]
                    ],
                }
            },
            "Invalid area",
            "self-intersecting",
        ),
        ({"bbox": [2.0, 41.3, 2.3, 41.5]}, "Invalid area", "maximum is 50"),
        (
            {
                "polygon": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [2.16 + 0.001 * math.cos(a), 41.39 + 0.001 * math.sin(a)]
                            for a in (2 * math.pi * i / 2_500 for i in range(2_501))
                        ]
                    ],
                }
            },
            "Invalid area",
            "maximum is 2,000",
        ),
        ({"district": "nowhere"}, "Invalid area", "unknown district"),
        ({}, "Invalid request", "exactly one of"),
        ({"district": "test", "bbox": [1, 2, 3, 4]}, "Invalid request", "exactly one of"),
        ({"polygon": {"type": "Point", "coordinates": [1, 2]}}, "Invalid request", "polygon"),
        ({"bbox": [3, 2, 1, 4]}, "Invalid area", "xmin < xmax"),
    ],
)
def test_invalid_requests_are_422_problem_details(
    client: APIClient, warehouse_path: Path, body: dict[str, Any], title: str, hint: str
) -> None:
    response = post(client, body)
    assert response.status_code == 422, response.content[:300]
    assert response["Content-Type"] == PROBLEM_JSON
    problem = response.json()
    assert set(problem) == {"type", "title", "status", "detail"}
    assert problem["status"] == 422 and problem["title"] == title
    assert hint in problem["detail"], problem["detail"]


# --- cache -------------------------------------------------------------------------------


@pytest.mark.django_db
def test_repeat_request_is_served_from_cache(client: APIClient, warehouse_path: Path) -> None:
    body = {"polygon": square(0, 0, 1_000, 1_000)}
    first, second = post(client, body).json(), post(client, body).json()
    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True
    assert {k: v for k, v in first.items() if k != "meta"} == {
        k: v for k, v in second.items() if k != "meta"
    }


@pytest.mark.django_db
def test_editing_a_definition_changes_the_next_response(
    client: APIClient, warehouse_path: Path
) -> None:
    body = {"polygon": square(0, 0, 1_000, 1_000)}
    before = post(client, body).json()["kpis"][0]
    assert before["band"] == "Calmed"

    row = KpiDefinition.objects.get(key="low_speed_street_share")
    row.label = "Edited in the admin"
    row.bands = [{"label": "Low", "max": 99.9}, {"label": "Everything", "max": None}]
    row.save()  # bumps updated_at -> new cache key, nothing to clear

    after = post(client, body).json()
    assert after["meta"]["cached"] is False
    assert after["kpis"][0]["label"] == "Edited in the admin"
    assert after["kpis"][0]["band"] == "Everything"


# --- warehouse lifecycle: missing, built, rebuilt — all without a restart --------------------


@pytest.mark.django_db
def test_missing_warehouse_is_503_until_built(client: APIClient, tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    with override_settings(WAREHOUSE_PATH=path):
        response = post(client, {"bbox": [2.15, 41.38, 2.16, 41.39]})
        assert response.status_code == 503
        assert response["Content-Type"] == PROBLEM_JSON
        assert "make load-data" in response.json()["detail"]
        assert client.get("/api/v1/districts").status_code == 503

        _build(path, speed=30)  # `make load-data` while the server runs
        response = post(client, {"polygon": square(0, 0, 1_000, 1_000)})
        assert response.status_code == 200
        assert response.json()["kpis"][0]["value"] == 100.0


@pytest.mark.django_db
def test_rebuilt_warehouse_is_picked_up_without_restart(client: APIClient, tmp_path: Path) -> None:
    path = tmp_path / "warehouse.duckdb"
    body = {"polygon": square(0, 0, 1_000, 1_000)}
    with override_settings(WAREHOUSE_PATH=path):
        _build(path, speed=30)
        first = post(client, body).json()
        assert first["kpis"][0]["value"] == 100.0

        _build(path, speed=50)  # a rebuild with different data, swapped in atomically
        second = post(client, body).json()
        assert second["kpis"][0]["value"] == 0.0
        assert second["meta"]["cached"] is False
        assert second["meta"]["warehouse_build"] != first["meta"]["warehouse_build"]


def _build(path: Path, *, speed: int) -> None:
    """What build.py does: write a temp file, then os.replace it over the live one."""
    tmp = path.with_suffix(".duckdb.tmp")
    tmp.unlink(missing_ok=True)
    wh = SyntheticWarehouse(tmp)
    wh.segment(100, 100, 600, 100, speed=speed)
    wh.close()
    os.replace(tmp, path)


# --- health and schema -------------------------------------------------------------------


def test_health_reports_missing_warehouse(client: APIClient, tmp_path: Path) -> None:
    with override_settings(WAREHOUSE_PATH=tmp_path / "missing.duckdb"):
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "warehouse": False}


def test_health_reports_present_warehouse(client: APIClient, tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    warehouse.write_bytes(b"")
    with override_settings(WAREHOUSE_PATH=warehouse):
        response = client.get("/api/v1/health")
    assert response.json() == {"status": "ok", "warehouse": True}


def test_openapi_schema_is_served(client: APIClient) -> None:
    response = client.get("/api/schema/")
    assert response.status_code == 200
    for path in (b"/api/v1/health", b"/api/v1/kpis", b"/api/v1/districts"):
        assert path in response.content
