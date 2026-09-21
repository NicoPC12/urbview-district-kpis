"""Serializers for the KPI API — the OpenAPI schema, and therefore the frontend types.

Every response field must be declared here: the schema is generated from these classes and
``schema.gen.ts`` from that schema, so an undeclared field does not exist for the client.
Output serializers read the engine's frozen dataclasses through ``source=`` paths; nothing is
copied into intermediate dicts. Fields that may be absent are declared ``required=False`` and
dropped when ``None`` (``OmitNoneMixin``), so the client sees ``field?: T``, never
``field: T | null`` for a merely optional value.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.areas.resolve import AreaRequest, AreaSource
from apps.kpis.engine import KpiResponse, Layer
from apps.kpis.registry import Denominator, SourceKind

# Several contract field names (`source`, `label`, `data`, `context`) shadow attributes the
# DRF stubs declare on `Field`/`Serializer`. DRF's metaclass pops declared fields out of the
# class namespace, so nothing is shadowed at runtime; the ignores are stub noise only.

# --- shared ------------------------------------------------------------------------------

GEOMETRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "GeoJSON geometry, EPSG:4326, coordinates rounded to 5 decimals (~1 m). The frontend "
        "narrows this to @types/geojson in one adapter (frontend/src/api/geojson.ts)."
    ),
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                "Point",
                "LineString",
                "Polygon",
                "MultiPoint",
                "MultiLineString",
                "MultiPolygon",
            ],
        },
        "coordinates": {"type": "array", "items": {}},
    },
    "required": ["type", "coordinates"],
}


@extend_schema_field(GEOMETRY_SCHEMA)
class GeometryField(serializers.JSONField):
    """A GeoJSON geometry already serialised by DuckDB; passed through untouched."""


class OmitNoneMixin:
    """Drop ``None`` values of ``required=False`` fields, so optional means absent."""

    def to_representation(self, instance: object) -> dict[str, Any]:
        """Serialise, then remove optional keys whose value is None."""
        data: dict[str, Any] = super().to_representation(instance)  # type: ignore[misc]
        fields: dict[str, serializers.Field[Any, Any, Any, Any]] = self.fields  # type: ignore[attr-defined]
        for name, field in fields.items():
            if not field.required and data.get(name) is None:
                data.pop(name, None)
        return data


class ProblemSerializer(serializers.Serializer[dict[str, Any]]):
    """RFC 7807 problem details; media type application/problem+json."""

    type = serializers.CharField(help_text='Always "about:blank".')
    title = serializers.CharField(help_text="Short classification, e.g. 'Invalid area'.")
    status = serializers.IntegerField()
    detail = serializers.CharField(help_text="A sentence a person can act on.")


# --- request -----------------------------------------------------------------------------


class PolygonSerializer(serializers.Serializer[dict[str, Any]]):
    """A GeoJSON Polygon in EPSG:4326: rings of [lon, lat] positions."""

    type = serializers.ChoiceField(choices=["Polygon"])
    coordinates = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=3),
            min_length=4,
        ),
        min_length=1,
    )


class KpiRequestSerializer(serializers.Serializer[dict[str, Any]]):
    """Exactly one of ``district``, ``bbox`` or ``polygon``."""

    district = serializers.CharField(required=False, help_text="District slug, e.g. eixample.")
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        min_length=4,
        max_length=4,
        required=False,
        help_text="[xmin, ymin, xmax, ymax] in EPSG:4326 (lon, lat).",
    )
    polygon = PolygonSerializer(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Exactly one selector."""
        given = [k for k in ("district", "bbox", "polygon") if k in attrs]
        if len(given) != 1:
            raise serializers.ValidationError(
                "exactly one of district, bbox or polygon is required"
                + (f" (got {', '.join(given)})" if given else "")
            )
        return attrs

    def to_area_request(self) -> AreaRequest:
        """The validated selector as the engine's value object."""
        data = self.validated_data
        bbox = data.get("bbox")
        return AreaRequest(
            district=data.get("district"),
            bbox=None if bbox is None else (bbox[0], bbox[1], bbox[2], bbox[3]),
            polygon=data.get("polygon"),
        )


# --- response ----------------------------------------------------------------------------


class AreaSerializer(serializers.Serializer[Any]):
    """The area the numbers describe."""

    name = serializers.CharField()
    km2 = serializers.FloatField()
    source = serializers.ChoiceField(choices=[(v.value, v.name) for v in AreaSource])  # type: ignore[assignment]
    district_overlap_share = serializers.FloatField(
        min_value=0,
        max_value=1,
        help_text="Share of the area that lies inside the loaded district, i.e. that has "
        "data. 1 for the district itself; 0 for a polygon drawn elsewhere.",
    )


class SourceSerializer(OmitNoneMixin, serializers.Serializer[Any]):
    """Where a KPI's band boundaries come from."""

    kind = serializers.ChoiceField(choices=[(v.value, v.name) for v in SourceKind])
    label = serializers.CharField()  # type: ignore[assignment]
    url = serializers.URLField(allow_null=True)
    note = serializers.CharField(required=False)


class BandSerializer(serializers.Serializer[Any]):
    """value <= max; the last band has max = null."""

    label = serializers.CharField()  # type: ignore[assignment]
    max = serializers.FloatField(allow_null=True)


class BreakdownItemSerializer(serializers.Serializer[Any]):
    """One slice of a KPI (a chart bar, a map category). Keys match layer feature categories."""

    key = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    value = serializers.FloatField()


class ContextItemSerializer(serializers.Serializer[Any]):
    """A figure needed to read the value, e.g. the share of streets with a mapped limit."""

    key = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField()


class KpiSerializer(OmitNoneMixin, serializers.Serializer[Any]):
    """One KPI: its number for this area and the metadata to read it honestly."""

    key = serializers.CharField(source="definition.key")
    label = serializers.CharField(source="definition.label")  # type: ignore[assignment]
    value = serializers.FloatField(
        source="row.value", allow_null=True, help_text="null when sample_size is 0."
    )
    unit = serializers.CharField(source="definition.spec.unit")
    band = serializers.CharField(allow_null=True)
    definition = serializers.CharField(source="definition.definition")
    not_claim = serializers.CharField(source="definition.not_claim")
    denominator = serializers.ChoiceField(
        source="definition.spec.denominator", choices=[(v.value, v.name) for v in Denominator]
    )
    lower_is_better = serializers.BooleanField(
        source="definition.spec.lower_is_better", help_text="Orders bands; never colours them."
    )
    source = SourceSerializer(source="definition.source")  # type: ignore[assignment]
    bands = BandSerializer(source="definition.bands", many=True)
    sample_size = serializers.IntegerField(
        source="row.sample_size", help_text="Features behind the number; 0 is the empty state."
    )
    breakdown = BreakdownItemSerializer(source="row.breakdown", many=True, required=False)
    breakdown_note = serializers.CharField(
        source="definition.breakdown_note",
        required=False,
        help_text="Present when the KPI deliberately has no breakdown, saying why.",
    )
    context = ContextItemSerializer(source="row.context", many=True)  # type: ignore[assignment]


class LegendItemSerializer(serializers.Serializer[Any]):
    """A category of one KPI's map layer and its colour."""

    kpi_key = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    color = serializers.CharField(help_text="#rrggbb")


class LegendSerializer(serializers.Serializer[Any]):
    """Every map category with its colour."""

    type = serializers.SerializerMethodField()
    items = LegendItemSerializer(source="legend", many=True)

    @extend_schema_field({"type": "string", "enum": ["categorical"]})
    def get_type(self, obj: KpiResponse) -> str:
        """Only categorical legends exist today."""
        return "categorical"


class FeaturePropertiesSerializer(OmitNoneMixin, serializers.Serializer[Any]):
    """Exactly what the frontend reads: the category to filter on and the contribution value."""

    category = serializers.CharField(help_text="Matches a breakdown/legend key of the KPI.")
    name = serializers.CharField(required=False, help_text="Street or park name, when mapped.")
    length_m = serializers.FloatField(required=False, help_text="Clipped length (streets).")
    distance_m = serializers.FloatField(
        required=False, help_text="Distance to the nearest target (building centroids)."
    )
    area_ha = serializers.FloatField(required=False, help_text="Green spaces.")


class FeatureSerializer(serializers.Serializer[Any]):
    """A GeoJSON Feature; ``id`` is the Overture GERS id."""

    type = serializers.ChoiceField(choices=["Feature"])
    id = serializers.CharField()
    geometry = GeometryField()
    properties = FeaturePropertiesSerializer()


class FeatureCollectionSerializer(serializers.Serializer[Any]):
    """A GeoJSON FeatureCollection in EPSG:4326."""

    type = serializers.ChoiceField(choices=["FeatureCollection"])
    features = FeatureSerializer(many=True)


class LayerSerializer(serializers.Serializer[Any]):
    """A map layer explaining one KPI."""

    id = serializers.CharField()
    kpi_key = serializers.CharField()
    data = serializers.SerializerMethodField()  # type: ignore[assignment]

    @extend_schema_field(FeatureCollectionSerializer)
    def get_data(self, obj: Layer) -> dict[str, Any]:
        """Features come out of DuckDB already serialised; wrap, do not re-walk them."""
        return {"type": "FeatureCollection", "features": list(obj.features)}


class LayersSerializer(serializers.Serializer[Any]):
    """Layer container (room for raster layers later without a breaking change)."""

    vectors = LayerSerializer(source="layers", many=True)


class MetaSerializer(serializers.Serializer[Any]):
    """Provenance and timing."""

    computed_ms = serializers.FloatField()
    cached = serializers.BooleanField()
    overture_release = serializers.CharField()
    warehouse_build = serializers.CharField(help_text="Short hash of the warehouse build.")
    timings_ms = serializers.DictField(
        child=serializers.FloatField(), help_text="Per KPI and per layer (layer:<id>)."
    )


class KpiResponseSerializer(serializers.Serializer[Any]):
    """POST /api/v1/kpis response."""

    area = AreaSerializer()
    kpis = KpiSerializer(many=True)
    insights = serializers.ListField(child=serializers.CharField())
    legend = LegendSerializer(source="*")
    layers = LayersSerializer(source="*")
    meta = MetaSerializer()


class DistrictSerializer(serializers.Serializer[Any]):
    """A district the API knows: what the map draws and fits to on load."""

    slug = serializers.CharField()
    name = serializers.CharField()
    km2 = serializers.FloatField()
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        min_length=4,
        max_length=4,
        help_text="[xmin, ymin, xmax, ymax] in EPSG:4326.",
    )
    geometry = GeometryField()


class HealthSerializer(serializers.Serializer[dict[str, object]]):
    """Liveness plus whether the DuckDB warehouse file is present."""

    status = serializers.ChoiceField(choices=["ok"])
    warehouse = serializers.BooleanField(
        help_text="True when data/warehouse.duckdb exists, i.e. `make load-data` has run."
    )
