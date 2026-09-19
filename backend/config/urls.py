"""URL routing.

Everything the frontend consumes lives under ``/api/v1/``. The OpenAPI schema at
``/api/schema/`` is the source of truth for the generated TypeScript types.
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("apps.kpis.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
