"""Admin for KPI metadata: thresholds and citations are data a planner can audit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest

from apps.kpis.models import KpiDefinition

if TYPE_CHECKING:  # ModelAdmin is generic only in django-stubs, not at runtime
    ModelAdminBase = admin.ModelAdmin[KpiDefinition]
else:
    ModelAdminBase = admin.ModelAdmin


@admin.register(KpiDefinition)
class KpiDefinitionAdmin(ModelAdminBase):
    """List by key; the key is fixed once created because it joins to code."""

    list_display = ("key", "label", "source_kind", "updated_at")
    fields = (
        "key",
        "label",
        "definition",
        "not_claim",
        "bands",
        ("source_kind", "source_label"),
        "source_url",
        "source_note",
        "breakdown_note",
        "updated_at",
    )

    def get_readonly_fields(
        self, request: HttpRequest, obj: KpiDefinition | None = None
    ) -> tuple[str, ...]:
        """The key is editable only on creation."""
        return ("key", "updated_at") if obj is not None else ("updated_at",)
