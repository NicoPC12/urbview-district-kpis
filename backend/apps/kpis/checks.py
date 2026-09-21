"""System check: the KPI keys in code and in the database must be the same set.

Registered with the ``database`` tag, so it runs on ``manage.py check --database default``
(the container runs that between ``migrate`` and ``runserver``). ``migrate`` itself also runs
database checks *before* applying anything, so on an empty database the table may not exist
yet: that case is skipped, and the explicit check right after ``migrate`` catches a mismatch.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.apps import AppConfig
from django.core.checks import Error, Tags, register
from django.db import connections

from apps.kpis import definitions
from apps.kpis.models import KpiDefinition


@register(Tags.database)
def registry_matches_database(
    app_configs: Sequence[AppConfig] | None,
    databases: Sequence[str] | None = None,
    **kwargs: object,
) -> list[Error]:
    """One error naming every key that exists on only one side."""
    if "default" not in (databases or ()):
        return []
    table = KpiDefinition._meta.db_table
    if table not in connections["default"].introspection.table_names():
        return []  # not migrated yet; `migrate` runs this check before applying migrations
    problem = definitions.mismatch(set(KpiDefinition.objects.values_list("key", flat=True)))
    if problem is None:
        return []
    return [Error(problem, id="kpis.E001")]
