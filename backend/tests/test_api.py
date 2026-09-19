"""API contract tests."""

from pathlib import Path

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


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


@pytest.mark.parametrize("path", ["/api/schema/"])
def test_openapi_schema_is_served(client: APIClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert b"/api/v1/health" in response.content
