"""App config: importing the system checks registers them."""

from django.apps import AppConfig


class KpisConfig(AppConfig):
    """The KPI app."""

    name = "apps.kpis"
    verbose_name = "KPIs"

    def ready(self) -> None:
        """Register the registry/database consistency check."""
        from apps.kpis import checks  # noqa: F401  (registration side effect)
