"""Rule-based insight sentences, generated from the numbers at request time.

Each rule is a predicate over the computed results plus a template that always embeds at
least one computed number. Rules are ordered by how much they matter to a safety reader;
the first ``MAX_INSIGHTS`` that fire are returned. Two areas with different values fire
different rules and format different numbers, which is what "not hardcoded" means here.
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


Rule = Callable[[Facts], str | None]


def _low_speed(f: Facts) -> str | None:
    v, km = f.value("low_speed_street_share"), f.context("low_speed_street_share", "mapped_km")
    if v is None or km is None:
        return None
    if v >= 70:
        return (
            f"{v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h or "
            f"less — a calmed street network."
        )
    if v < 40:
        return (
            f"Only {v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h "
            f"or less; most of it is posted at 50."
        )
    return (
        f"{v:.0f}% of the {km:.1f} km of carriageway with a mapped limit is 30 km/h or "
        f"less — a mix of calmed streets and 50 km/h corridors."
    )


def _limit_coverage(f: Facts) -> str | None:
    cov = f.context("low_speed_street_share", "limit_coverage")
    if cov is None or cov >= 75:
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
            f"Half of the {n:,} buildings are within {v:.0f} m of a green space of at least "
            f"0.5 ha — inside the WHO 300 m rule of thumb ({share:.0f}% are)."
        )
    within = "none" if share == 0 else f"only {share:.0f}%"
    return (
        f"The median building is {v:.0f} m from the nearest green space of at least 0.5 "
        f"ha; {within} of the {n:,} buildings are within the WHO 300 m rule of thumb."
    )


def _crossings(f: Facts) -> str | None:
    v, n = f.value("crossing_density"), f.context("crossing_density", "crossings")
    if v is None or n is None:
        return None
    if v < 10:
        return (
            f"{n:.0f} mapped crossings give {v:.1f} per km of carriageway — sparse crossing "
            f"provision for pedestrians."
        )
    if v >= 20:
        return (
            f"{n:.0f} mapped crossings give {v:.1f} per km of carriageway — one roughly "
            f"every {1000 / v:.0f} m."
        )
    return None


def _pedestrian(f: Facts) -> str | None:
    v, km = (
        f.value("pedestrian_network_share"),
        f.context("pedestrian_network_share", "pedestrian_km"),
    )
    if v is None or km is None:
        return None
    if v >= 60:
        return (
            f"{v:.0f}% of the mapped network ({km:.1f} km) is pedestrian-only — walking "
            f"infrastructure dominates."
        )
    if v < 30:
        return (
            f"Only {v:.0f}% of the mapped network ({km:.1f} km) is pedestrian-only; the area "
            f"is laid out for vehicles."
        )
    return None


def _trees(f: Facts) -> str | None:
    v, n = f.value("street_tree_density"), f.context("street_tree_density", "trees")
    if v is None or n is None:
        return None
    if v >= 50:
        return (
            f"{n:.0f} mapped street trees, {v:.0f} per km of carriageway — one roughly every "
            f"{1000 / v:.0f} m."
        )
    if v < 20:
        return f"Only {n:.0f} mapped street trees, {v:.0f} per km of carriageway."
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
