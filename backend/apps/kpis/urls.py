"""Routes under ``/api/v1/``."""

from django.urls import path

from apps.kpis.views import DistrictListView, HealthView, KpiView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("districts", DistrictListView.as_view(), name="districts"),
    path("kpis", KpiView.as_view(), name="kpis"),
]
