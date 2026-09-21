"""HTTP views. Views validate, call a service, serialize — no business logic here."""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.areas.resolve import InvalidAreaError
from apps.kpis import service
from apps.kpis.problems import PROBLEM_JSON, Problem
from apps.kpis.serializers import (
    DistrictSerializer,
    HealthSerializer,
    KpiRequestSerializer,
    KpiResponseSerializer,
    ProblemSerializer,
)
from warehouse.connection import WarehouseMissingError

WAREHOUSE_MISSING = (
    "The warehouse has not been built yet: run `make load-data` (about 10 s with the "
    "prepared extract), then retry. The server does not need restarting."
)


class KpiView(APIView):
    """``POST /api/v1/kpis``: every KPI for a district, a bbox or a drawn polygon."""

    @extend_schema(
        operation_id="kpis",
        request=KpiRequestSerializer,
        responses={
            200: KpiResponseSerializer,
            (422, PROBLEM_JSON): ProblemSerializer,
            (503, PROBLEM_JSON): ProblemSerializer,
        },
        description=(
            "Compute every KPI for the given area. Exactly one of district, bbox or polygon. "
            "An area with no data (e.g. drawn outside the district) is a 200 with "
            "sample_size 0 and value null on every KPI, not an error."
        ),
    )
    def post(self, request: Request) -> Response:
        """Validate the selector, compute (or serve from cache), return."""
        selector = KpiRequestSerializer(data=request.data)
        selector.is_valid(raise_exception=True)
        try:
            data = service.kpis(selector.to_area_request())
        except InvalidAreaError as exc:
            raise Problem(422, "Invalid area", str(exc)) from exc
        except WarehouseMissingError as exc:
            raise Problem(503, "Warehouse not built", WAREHOUSE_MISSING) from exc
        return Response(data)


class DistrictListView(APIView):
    """``GET /api/v1/districts``: the districts the API knows, with outlines."""

    @extend_schema(
        operation_id="districts",
        responses={200: DistrictSerializer(many=True), (503, PROBLEM_JSON): ProblemSerializer},
    )
    def get(self, request: Request) -> Response:
        """List districts (outline geometry from the warehouse)."""
        try:
            return Response(service.districts())
        except WarehouseMissingError as exc:
            raise Problem(503, "Warehouse not built", WAREHOUSE_MISSING) from exc


class HealthView(APIView):
    """Liveness probe that also reports whether the warehouse has been built.

    The frontend shows this on first load so a reviewer who has run ``docker compose up``
    but not yet ``make load-data`` sees *why* there are no numbers.
    """

    @extend_schema(responses=HealthSerializer, operation_id="health")
    def get(self, request: Request) -> Response:
        """Return ``{"status": "ok", "warehouse": <bool>}``."""
        payload = {"status": "ok", "warehouse": settings.WAREHOUSE_PATH.is_file()}
        return Response(HealthSerializer(payload).data)
