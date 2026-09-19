"""Shared pytest fixtures."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    """Unauthenticated API client (the API has no auth)."""
    return APIClient()
