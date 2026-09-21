"""Editable KPI metadata: the half of a KPI a planner can audit and change without a deploy.

The computational half (SQL, unit, denominator) lives in :mod:`apps.kpis.registry`; the key
is the join. ``updated_at`` feeds the response cache key, so editing a threshold in the admin
invalidates every cached response without anyone clearing anything.
"""

from __future__ import annotations

from django.db import models

from apps.kpis.registry import SourceKind


class KpiDefinition(models.Model):
    """Label, definition, "does not claim", bands and source of one KPI."""

    key = models.SlugField(max_length=64, unique=True, help_text="Matches a KpiSpec in code.")
    label = models.CharField(max_length=120)
    definition = models.TextField(help_text="One or two sentences: what this measures.")
    not_claim = models.TextField(
        verbose_name="does not claim",
        help_text="What this number explicitly does not tell you. Rendered on the card.",
    )
    bands = models.JSONField(
        help_text='Ordered list of {"label": str, "max": number | null}; a value falls into '
        "the first band whose max it does not exceed. The last band must have max = null."
    )
    source_kind = models.CharField(max_length=16, choices=[(k.value, k.value) for k in SourceKind])
    source_label = models.CharField(max_length=200)
    source_url = models.URLField(blank=True, default="")
    source_note = models.TextField(blank=True, default="")
    breakdown_note = models.TextField(
        blank=True, default="", help_text="Set when the KPI deliberately has no breakdown."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "KPI definition"
        ordering = ["key"]

    def __str__(self) -> str:
        """Key and label, for the admin."""
        return f"{self.key}: {self.label}"
