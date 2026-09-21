"""The KPI registry: one frozen definition per KPI, nothing computed here.

Adding a KPI is one SQL file + one entry here + one test (CLAUDE.md §8). Every band boundary
either cites a source that was read, or is marked ``chosen`` with the reasoning; see NOTES.md
for the long form. ``REGISTRY_VERSION`` is part of the response cache key: bump it whenever a
definition changes in a way that alters output.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

from warehouse.connection import LAYERS_DIR, QUERIES_DIR

REGISTRY_VERSION = "2026-09-21.1"


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
class KpiDefinition:
    """Everything the API says about a KPI that is not a number."""

    key: str
    label: str
    unit: str
    denominator: Denominator
    definition: str
    not_claim: str
    source: Source
    bands: tuple[Band, ...]
    sql: Path
    layers: tuple[LayerDefinition, ...]
    colors: Mapping[str, str]
    """Colour per breakdown key / layer category. Categories missing here use ``DEFAULT_COLOR``."""
    breakdown_note: str | None = None
    """Set when the KPI deliberately has no breakdown, saying why."""
    lower_is_better: bool = False

    def band_for(self, value: float | None) -> str | None:
        """Label of the first band whose ``max`` the value does not exceed."""
        if value is None:
            return None
        for band in self.bands:
            if band.max is None or value <= band.max:
                return band.label
        return self.bands[-1].label


DEFAULT_COLOR = "#94a3b8"  # slate-400: "other"

# A small, colour-blind-safe set reused across KPIs; semantic order good -> bad where it applies.
GOOD, MID, BAD, NEUTRAL = "#15803d", "#ca8a04", "#b91c1c", "#64748b"

LOW_SPEED_STREET_SHARE = KpiDefinition(
    key="low_speed_street_share",
    label="Carriageway limited to 30 km/h or less",
    unit="%",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    definition=(
        "Share of carriageway length inside the area whose posted speed limit is 30 km/h or "
        "lower, over the carriageway length that has a mapped limit at all."
    ),
    not_claim=(
        "A posted limit, not an observed speed. Carriageway without a mapped limit is "
        "excluded from both numerator and denominator, not assumed fast; the share excluded "
        "is shown alongside. Says nothing about enforcement, crashes or lane count."
    ),
    source=Source(
        kind=SourceKind.CITATION,
        label="Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC",
        url="https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969",
        note=(
            "The 30 km/h threshold is the statutory urban limit for roads with one lane per "
            "direction since 11 May 2021. The band boundaries at 40 % and 70 % are chosen: "
            "the district reads 50.7 %, and the bands separate a superblock interior from a "
            "through-route corridor."
        ),
    ),
    bands=(Band("Mostly 50", 40), Band("Mixed", 70), Band("Calmed", None)),
    sql=QUERIES_DIR / "low_speed_street_share.sql",
    layers=(LayerDefinition("streets_speed", LAYERS_DIR / "streets_speed.sql"),),
    colors=MappingProxyType(
        {"le20": "#166534", "le30": GOOD, "le50": BAD, "gt50": "#7f1d1d", "none": DEFAULT_COLOR}
    ),
)

CROSSING_DENSITY = KpiDefinition(
    key="crossing_density",
    label="Pedestrian crossings per km of carriageway",
    unit="/km",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    definition=(
        "Mapped pedestrian crossing points inside the area per kilometre of carriageway "
        "inside the area."
    ),
    not_claim=(
        "A crossing point carries no quality: signalised, raised, marked or lit are not "
        "known. High density does not mean safe crossing, and a pedestrianised area with no "
        "carriageway has nothing to cross and reads as no data, not as zero."
    ),
    source=Source(
        kind=SourceKind.CHOSEN,
        label="Chosen: half and roughly the district mean",
        url=None,
        note=(
            "No standard I could verify prescribes crossings per kilometre. The district "
            "reads 22.6/km; bands at 10 and 20 make blocks below the district norm read as such."
        ),
    ),
    bands=(Band("Sparse", 10), Band("Moderate", 20), Band("Dense", None)),
    sql=QUERIES_DIR / "crossing_density.sql",
    layers=(LayerDefinition("crossings", LAYERS_DIR / "crossings.sql"),),
    colors=MappingProxyType({"crossing": "#1d4ed8"}),
    breakdown_note=(
        "No breakdown: Overture carries no attributes on a crossing point to split by."
    ),
)

PEDESTRIAN_NETWORK_SHARE = KpiDefinition(
    key="pedestrian_network_share",
    label="Network length that is pedestrian-only",
    unit="%",
    denominator=Denominator.NETWORK_LENGTH_M,
    definition=(
        "Share of all mapped network length inside the area that is pedestrian-only geometry "
        "(footways, pedestrian streets, steps, paths)."
    ),
    not_claim=(
        "Not comparable across cities: Overture maps sidewalks here as separate geometry, "
        "which inflates pedestrian kilometres relative to places that map sidewalks as road "
        "attributes. Says nothing about sidewalk width, quality or continuity."
    ),
    source=Source(
        kind=SourceKind.CHOSEN,
        label="Chosen: bands bracket the district figure",
        url=None,
        note=(
            "The district reads 52 %. Bands at 30 % and 60 % let pedestrianised streets and "
            "superblocks (higher) and through-route blocks (lower) separate."
        ),
    ),
    bands=(Band("Car-dominated", 30), Band("Mixed", 60), Band("Walking-first", None)),
    sql=QUERIES_DIR / "pedestrian_network_share.sql",
    layers=(LayerDefinition("streets_class", LAYERS_DIR / "streets_class.sql"),),
    colors=MappingProxyType(
        {
            "footway": GOOD,
            "pedestrian": "#166534",
            "steps": "#4d7c0f",
            "path": "#65a30d",
            "cycleway": "#0e7490",
            "living_street": "#a16207",
            "residential": MID,
            "tertiary": "#c2410c",
            "secondary": BAD,
            "primary": "#7f1d1d",
            "service": NEUTRAL,
            "unknown": DEFAULT_COLOR,
        }
    ),
)

GREEN_SPACE_DISTANCE_P50 = KpiDefinition(
    key="green_space_distance_p50",
    label="Median distance to a green space of at least 0.5 ha",
    unit="m",
    denominator=Denominator.BUILDING_COUNT,
    definition=(
        "Median straight-line distance from a building centroid inside the area to the "
        "nearest mapped green space of at least 0.5 ha, wherever that green space lies; the "
        "size floor and the 300 m band follow WHO Europe (2017)."
    ),
    not_claim=(
        "Straight-line, not walking distance: a park across a railway reads as near. Only "
        "polygons Overture carries count, so interior courtyard gardens and pocket greens "
        "under 0.5 ha are ignored by design. Building centroids are not people."
    ),
    source=Source(
        kind=SourceKind.CITATION,
        label="WHO Europe, Urban green spaces: a brief for action (2017), p. 11",
        url="https://www.who.int/europe/publications/i/item/9789289052498",
        note=(
            '"urban residents should be able to access public green spaces of at least '
            "0.5–1 hectare within 300 metres' linear distance (around 5 minutes' walk) of "
            'their homes." The 600 m boundary is chosen: double the WHO distance.'
        ),
    ),
    bands=(Band("Within WHO rule of thumb", 300), Band("Beyond", 600), Band("Far", None)),
    sql=QUERIES_DIR / "green_space_distance_p50.sql",
    layers=(
        LayerDefinition("buildings_green", LAYERS_DIR / "buildings_green.sql"),
        LayerDefinition("green_spaces", LAYERS_DIR / "green_spaces.sql"),
    ),
    colors=MappingProxyType(
        {"within_300": GOOD, "within_600": MID, "beyond_600": BAD, "green_space": "#22c55e"}
    ),
    lower_is_better=True,
)

STREET_TREE_DENSITY = KpiDefinition(
    key="street_tree_density",
    label="Street trees per km of carriageway",
    unit="/km",
    denominator=Denominator.CARRIAGEWAY_LENGTH_M,
    definition=(
        "Mapped individual trees inside the area per kilometre of carriageway inside the area."
    ),
    not_claim=(
        "A shade and greenness proxy, not a safety measure. Canopy size, species and health "
        "are unknown; a sapling counts the same as a plane tree. Tree mapping is OSM-derived "
        "and can be uneven outside this district."
    ),
    source=Source(
        kind=SourceKind.CHOSEN,
        label="Chosen: district mean and less than half of it",
        url=None,
        note="The district reads 55/km with every full 1 km cell between 752 and 2,001 trees.",
    ),
    bands=(Band("Sparse", 20), Band("Moderate", 50), Band("Dense", None)),
    sql=QUERIES_DIR / "street_tree_density.sql",
    layers=(LayerDefinition("trees", LAYERS_DIR / "trees.sql"),),
    colors=MappingProxyType({"tree": "#16a34a"}),
    breakdown_note="No breakdown: Overture tree points carry no species, size or canopy.",
)

KPIS: tuple[KpiDefinition, ...] = (
    LOW_SPEED_STREET_SHARE,
    CROSSING_DENSITY,
    PEDESTRIAN_NETWORK_SHARE,
    GREEN_SPACE_DISTANCE_P50,
    STREET_TREE_DENSITY,
)

BY_KEY: Mapping[str, KpiDefinition] = MappingProxyType({k.key: k for k in KPIS})
