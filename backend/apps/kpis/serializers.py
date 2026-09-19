"""Serializers for the KPI API.

Every response field must be declared here: the OpenAPI schema is generated from these
classes and the frontend types are generated from that schema, so an undeclared field does
not exist as far as the client is concerned.
"""

from rest_framework import serializers


class HealthSerializer(serializers.Serializer[dict[str, object]]):
    """Liveness plus whether the DuckDB warehouse file is present."""

    status = serializers.ChoiceField(choices=["ok"])
    warehouse = serializers.BooleanField(
        help_text="True when data/warehouse.duckdb exists, i.e. `make load-data` has run."
    )
