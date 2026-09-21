"""Admin for the district catalogue."""

from typing import TYPE_CHECKING

from django.contrib import admin

from apps.areas.models import District

if TYPE_CHECKING:  # ModelAdmin is generic only in django-stubs, not at runtime
    ModelAdminBase = admin.ModelAdmin[District]
else:
    ModelAdminBase = admin.ModelAdmin


@admin.register(District)
class DistrictAdmin(ModelAdminBase):
    """Read-mostly: districts are added by loading data, not by hand."""

    list_display = ("slug", "name", "overture_id")
