"""Shared pytest fixtures."""

import pytest
from rest_framework.test import APIClient

from apps.kpis import definitions
from apps.kpis.registry import Kpi


@pytest.fixture
def client() -> APIClient:
    """Unauthenticated API client (the API has no auth)."""
    return APIClient()


@pytest.fixture
def kpis(db: None) -> tuple[Kpi, ...]:
    """The KPI list as the engine sees it: code specs joined with the seeded metadata."""
    return definitions.load().kpis
