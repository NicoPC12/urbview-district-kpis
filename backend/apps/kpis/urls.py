"""Routes under ``/api/v1/``."""

from django.urls import path

from apps.kpis.views import HealthView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
]
