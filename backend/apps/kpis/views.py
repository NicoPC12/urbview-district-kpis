"""HTTP views. Views validate, call a service, serialize — no business logic here."""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.kpis.serializers import HealthSerializer


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
