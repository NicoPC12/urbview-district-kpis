"""Join the code registry with the database metadata into the KPI list the engine runs.

One query per request, never one per KPI. A key present on only one side is a configuration
error and is raised, never skipped: silently dropping a KPI is how a dashboard loses a card
without anyone noticing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.kpis.models import KpiDefinition
from apps.kpis.registry import SPECS, Band, Kpi, Source, SourceKind


class RegistryMismatchError(RuntimeError):
    """The set of KPI keys in code and in the database differ."""


@dataclass(frozen=True)
class Definitions:
    """The loaded KPI list plus the newest metadata timestamp (part of the cache key)."""

    kpis: tuple[Kpi, ...]
    updated_at: datetime | None


def mismatch(db_keys: set[str]) -> str | None:
    """Description of a code/database key mismatch, or None when both sides agree."""
    code_keys = {s.key for s in SPECS}
    missing_rows = sorted(code_keys - db_keys)
    orphan_rows = sorted(db_keys - code_keys)
    if not missing_rows and not orphan_rows:
        return None
    parts = []
    if missing_rows:
        parts.append(f"KPIs in code without a KpiDefinition row: {missing_rows}")
    if orphan_rows:
        parts.append(f"KpiDefinition rows without a KpiSpec in code: {orphan_rows}")
    return "; ".join(parts) + ". Add a data migration or a KpiSpec so both sides agree."


def from_row(row: KpiDefinition) -> Kpi:
    """Build one :class:`Kpi` from its spec and its metadata row."""
    return Kpi(
        spec=next(s for s in SPECS if s.key == row.key),
        label=row.label,
        definition=row.definition,
        not_claim=row.not_claim,
        source=Source(
            kind=SourceKind(row.source_kind),
            label=row.source_label,
            url=row.source_url or None,
            note=row.source_note or None,
        ),
        bands=tuple(Band(str(b["label"]), b["max"]) for b in row.bands),
        breakdown_note=row.breakdown_note or None,
    )


def load() -> Definitions:
    """Every KPI in registry order, with metadata from the database (one query).

    Raises:
        RegistryMismatchError: a key exists on only one side.
    """
    rows = {row.key: row for row in KpiDefinition.objects.all()}
    problem = mismatch(set(rows))
    if problem is not None:
        raise RegistryMismatchError(problem)
    kpis = tuple(from_row(rows[spec.key]) for spec in SPECS)
    return Definitions(kpis=kpis, updated_at=max(r.updated_at for r in rows.values()))
