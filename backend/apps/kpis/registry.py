"""The KPI registry: what the *code* owns about each KPI — the computation.

Source of truth is split on purpose (Phase 4 decision):

- **Code** (this module) owns everything that changes the number: the key, the SQL file, the
  unit, the denominator, the map layers, the category colours (they name category keys the SQL
  emits) and whether lower is better (used only to *order* bands).
- **Postgres** (:class:`apps.kpis.models.KpiDefinition`) owns the editable metadata a planner
  audits: label, definition, ``not_claim``, bands, source and ``breakdown_note``. A data
  migration seeds it; the Django admin edits it; the system check in :mod:`apps.kpis.checks`
  refuses to start when the two sides disagree on the set of keys.

:func:`apps.kpis.definitions.load` joins the two into :class:`Kpi` once per request.
Adding a KPI is one SQL file + one :class:`KpiSpec` here + one metadata row + one test.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from warehouse.connection import LAYERS_DIR, QUERIES_DIR


class SourceKind(StrEnum):
    """How a band boundary is justified."""

    CITATION = "citation"
    DERIVED = "derived"
    CHOSEN = "chosen"


class Denominator(StrEnum):
    """Legal denominators (CLAUDE.md rule 2). No socioeconomic quantity, ever."""

    CARRIAGEWAY_LENGTH_M = "carriageway_length_m"
    NETWORK_LENGTH_M = "network_length_m"
    BUILDING_COUNT = "building_count"


@dataclass(frozen=True)
class Source:
    """Where a threshold comes from."""

    kind: SourceKind
    label: str
    url: str | None
    note: str | None = None


@dataclass(frozen=True)
class Band:
    """A band is "value <= max"; the last band has ``max = None`` and catches the rest."""

    label: str
    max: float | None


@dataclass(frozen=True)
class LayerDefinition:
    """A map layer that explains a KPI: a SQL file returning GeoJSON Features."""

    id: str
    sql: Path


@dataclass(frozen=True)
class KpiSpec:
    """The computational half of a KPI. Nothing here is editable without a code change."""

    key: str
    unit: str
    denominator: Denominator
    sql: Path
    layers: tuple[LayerDefinition, ...]
    colors: Mapping[str, str]
    """Colour per breakdown key / layer category. Categories missing here use ``DEFAULT_COLOR``.
    Categorical hues, never red: a red feature reads as "dangerous" (CLAUDE.md rule 4)."""
    lower_is_better: bool = False
    """Orders the bands best-first for display. Never colours them."""


@dataclass(frozen=True)
class Kpi:
    """A KPI as the engine sees it: the code spec joined with its database metadata."""

    spec: KpiSpec
    label: str
    definition: str
    not_claim: str
    source: Source
    bands: tuple[Band, ...]
    breakdown_note: str | None = None
    """Set when the KPI deliberately has no breakdown, saying why."""

    @property
    def key(self) -> str:
        """The KPI key."""
        return self.spec.key

    def band_for(self, value: float | None) -> str | None:
        """Label of the first band whose ``max`` the value does not exceed."""
        if value is None:
            return None
        for band in self.bands:
            if band.max is None or value <= band.max:
                return band.label
        return self.bands[-1].label


DEFAULT_COLOR = "#94a3b8"  # slate-400: "other"

# Categorical palette for map features: distinct hues, no red. Sequential band colours for the
# cards are a single blue ramp on the frontend; see NOTES.md "Palette".
GREEN, TEAL, BLUE, INDIGO, VIOLET, AMBER, BROWN, SLATE = (
    "#15803d",
    "#0f766e",
    "#1d4ed8",
    "#4338ca",
    "#7e22ce",
    "#b45309",
    "#78350f",
    "#64748b",
)

LOW_SPEED_STREET_SHARE = KpiSpec(
    key="low_speed_street_share",
    unit="%",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    sql=QUERIES_DIR / "low_speed_street_share.sql",
    layers=(LayerDefinition("streets_speed", LAYERS_DIR / "streets_speed.sql"),),
    colors=MappingProxyType(
        {"le20": GREEN, "le30": TEAL, "le50": AMBER, "gt50": BROWN, "none": DEFAULT_COLOR}
    ),
)

CROSSING_DENSITY = KpiSpec(
    key="crossing_density",
    unit="/km",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    sql=QUERIES_DIR / "crossing_density.sql",
    layers=(LayerDefinition("crossings", LAYERS_DIR / "crossings.sql"),),
    colors=MappingProxyType({"crossing": BLUE}),
)

PEDESTRIAN_NETWORK_SHARE = KpiSpec(
    key="pedestrian_network_share",
    unit="%",
    denominator=Denominator.NETWORK_LENGTH_M,
    sql=QUERIES_DIR / "pedestrian_network_share.sql",
    layers=(LayerDefinition("streets_class", LAYERS_DIR / "streets_class.sql"),),
    colors=MappingProxyType(
        {
            "footway": GREEN,
            "pedestrian": "#166534",
            "steps": "#4d7c0f",
            "path": "#65a30d",
            "cycleway": TEAL,
            "living_street": "#a16207",
            "residential": AMBER,
            "tertiary": BROWN,
            "secondary": INDIGO,
            "primary": VIOLET,
            "service": SLATE,
            "unknown": DEFAULT_COLOR,
        }
    ),
)

GREEN_SPACE_DISTANCE_P50 = KpiSpec(
    key="green_space_distance_p50",
    unit="m",
    denominator=Denominator.BUILDING_COUNT,
    sql=QUERIES_DIR / "green_space_distance_p50.sql",
    layers=(
        LayerDefinition("buildings_green", LAYERS_DIR / "buildings_green.sql"),
        LayerDefinition("green_spaces", LAYERS_DIR / "green_spaces.sql"),
    ),
    colors=MappingProxyType(
        {"within_300": GREEN, "within_600": AMBER, "beyond_600": VIOLET, "green_space": "#22c55e"}
    ),
    lower_is_better=True,
)

STREET_TREE_DENSITY = KpiSpec(
    key="street_tree_density",
    unit="/km",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    sql=QUERIES_DIR / "street_tree_density.sql",
    layers=(LayerDefinition("trees", LAYERS_DIR / "trees.sql"),),
    colors=MappingProxyType({"tree": "#16a34a"}),
)

SPECS: tuple[KpiSpec, ...] = (
    LOW_SPEED_STREET_SHARE,
    CROSSING_DENSITY,
    PEDESTRIAN_NETWORK_SHARE,
    GREEN_SPACE_DISTANCE_P50,
    STREET_TREE_DENSITY,
)

SPEC_BY_KEY: Mapping[str, KpiSpec] = MappingProxyType({s.key: s for s in SPECS})
