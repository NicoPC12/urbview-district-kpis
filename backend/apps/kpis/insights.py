"""Rule-based insight sentences, generated from the numbers at request time.

Each rule is a predicate over the computed results plus a template that always embeds at
least one computed number. Rules are ordered by how much they matter to a safety reader;
the first ``MAX_INSIGHTS`` that fire are returned. Two areas with different values fire
different rules and format different numbers, which is what "not hardcoded" means here.

Rules never carry their own thresholds: they read the KPI's *band* (whose boundaries come
from the database, derived or cited), so an edit in the admin moves the sentences too.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.areas.resolve import ResolvedArea
    from apps.kpis.engine import KpiResult

MAX_INSIGHTS = 5


@dataclass(frozen=True)
class Facts:
    """The values the rules read, looked up once."""

    results: dict[str, KpiResult]
    area: ResolvedArea

    def value(self, key: str) -> float | None:
        """A KPI value, or None when the KPI is absent or empty."""
        result = self.results.get(key)
        return None if result is None else result.row.value

    def context(self, key: str, item: str) -> float | None:
        """A KPI context figure by key."""
        result = self.results.get(key)
        if result is None:
            return None
        for ctx in result.row.context:
            if ctx.key == item:
                return ctx.value
        return None

    def sample(self, key: str) -> int:
        """A KPI's sample size (0 when absent)."""
        result = self.results.get(key)
        return 0 if result is None else result.row.sample_size

    def position(self, key: str) -> str | None:
        """``"low"`` / ``"mid"`` / ``"high"``: which band the value fell in, first to last."""
        result = self.results.get(key)
        if result is None or result.band is None:
            return None
        labels = [b.label for b in result.definition.bands]
        index = labels.index(result.band)
        if index == 0:
            return "low"
        return "high" if index == len(labels) - 1 else "mid"


Rule = Callable[[Facts], str | None]


def _low_speed(f: Facts) -> str | None:
    key = "low_speed_street_share"
    v, km, pos = f.value(key), f.context(key, "mapped_km"), f.position(key)
    if v is None or km is None:
        return None
    if pos == "high":
        return (
            f"{v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h or "
            f"less — a higher share than two thirds of Eixample's 250 m cells."
        )
    if pos == "low":
        return (
            f"Only {v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h "
            f"or less — a lower share than two thirds of Eixample's 250 m cells."
        )
    return (
        f"{v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h or "
        f"less — the middle third of Eixample's 250 m cells."
    )


# Chosen (NOTES.md): below this share of carriageway with a mapped limit, the speed KPI
# rests on a minority of the streets and the reader is told so.
LIMIT_COVERAGE_WARN = 75.0


def _limit_coverage(f: Facts) -> str | None:
    cov = f.context("low_speed_street_share", "limit_coverage")
    if cov is None or cov >= LIMIT_COVERAGE_WARN:
        return None
    return (
        f"Only {cov:.0f}% of the carriageway here has a mapped speed limit, so the speed "
        f"figure rests on a minority of the streets."
    )


def _green(f: Facts) -> str | None:
    v, n, share = (
        f.value("green_space_distance_p50"),
        f.sample("green_space_distance_p50"),
        f.context("green_space_distance_p50", "share_within_300"),
    )
    if v is None or share is None:
        return None
    if v <= 300:
        return (
            f"Half of the {n:,} buildings are within {v:.0f} m of a public green space of at "
            f"least 0.5 ha — inside the WHO 300 m rule of thumb ({share:.0f}% are)."
        )
    within = "none" if share == 0 else f"only {share:.0f}%"
    return (
        f"The median building is {v:.0f} m from the nearest public green space of at least "
        f"0.5 ha; {within} of the {n:,} buildings are within the WHO 300 m rule of thumb."
    )


def _crossings(f: Facts) -> str | None:
    key = "crossing_density"
    v, n, pos = f.value(key), f.context(key, "crossings"), f.position(key)
    if v is None or n is None or v <= 0:
        return None
    if pos == "low":
        return (
            f"{n:.0f} mapped crossings give {v:.1f} per km of carriageway — one every "
            f"{1000 / v:.0f} m, fewer than in two thirds of Eixample's 250 m cells."
        )
    if pos == "high":
        return (
            f"{n:.0f} mapped crossings give {v:.1f} per km of carriageway — one every "
            f"{1000 / v:.0f} m, more than in two thirds of Eixample's 250 m cells."
        )
    return None


def _pedestrian(f: Facts) -> str | None:
    key = "pedestrian_network_share"
    v, km, pos = f.value(key), f.context(key, "pedestrian_km"), f.position(key)
    if v is None or km is None:
        return None
    if pos == "high":
        return (
            f"{v:.0f}% of the street network ({km:.1f} km) is pedestrian-only space — more "
            f"than in two thirds of Eixample's 250 m cells."
        )
    if pos == "low":
        return (
            f"Only {v:.0f}% of the street network ({km:.1f} km) is pedestrian-only space — "
            f"less than in two thirds of Eixample's 250 m cells."
        )
    return None


def _trees(f: Facts) -> str | None:
    key = "street_tree_density"
    v, n, pos = f.value(key), f.context(key, "trees"), f.position(key)
    if v is None or n is None:
        return None
    if pos == "high" and v > 0:
        return (
            f"{n:.0f} mapped street trees, {v:.0f} per km of carriageway — one roughly every "
            f"{1000 / v:.0f} m, more than in two thirds of Eixample's 250 m cells."
        )
    if pos == "low":
        return (
            f"Only {n:.0f} mapped street trees, {v:.0f} per km of carriageway — fewer than "
            f"in two thirds of Eixample's 250 m cells."
        )
    return None


def _empty(f: Facts) -> str | None:
    empty = [r.definition.label for r in f.results.values() if r.row.sample_size == 0]
    if not empty:
        return None
    if len(empty) == len(f.results):
        return (
            f"The {f.area.km2:.2f} km² area contains none of the features the KPIs measure; "
            f"try a larger or different polygon."
        )
    return (
        f"No data for {len(empty)} of {len(f.results)} KPIs in this {f.area.km2:.2f} km² "
        f"area (e.g. {empty[0]})."
    )


def _overlap(f: Facts) -> str | None:
    share = f.area.district_overlap_share
    if share >= 0.95 or share == 0:  # entirely outside is already covered by _empty
        return None
    return (
        f"Only {share:.0%} of this {f.area.km2:.2f} km² area lies inside the loaded district; "
        f"the numbers describe that part alone."
    )


RULES: tuple[Rule, ...] = (
    _empty,
    _overlap,
    _low_speed,
    _limit_coverage,
    _green,
    _crossings,
    _pedestrian,
    _trees,
)


def generate(results: Iterable[KpiResult], area: ResolvedArea) -> list[str]:
    """Insight sentences for this area, most important first."""
    facts = Facts({r.key: r for r in results}, area)
    sentences = [s for rule in RULES if (s := rule(facts)) is not None]
    return sentences[:MAX_INSIGHTS]
