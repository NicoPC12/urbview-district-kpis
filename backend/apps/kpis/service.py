"""The request lifecycle behind the views: catalogue → cursor → resolve → cache → engine.

Cache key = sha256(normalised area WKT + warehouse build hash + newest KpiDefinition edit).
Rebuilding the warehouse or editing a threshold in the admin changes the key, so nothing ever
needs clearing. Locmem is process-local and is the right size for one dev container; drawn
polygons essentially never repeat, so in practice the cache serves the district and repeats
of it (README "Caching").
"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.areas.models import District
from apps.areas.resolve import AreaRequest, DistrictRef, resolve
from apps.kpis import definitions, engine
from apps.kpis.serializers import DistrictSerializer, KpiResponseSerializer
from warehouse import area as warehouse_area
from warehouse.connection import Warehouse

_warehouses: dict[Path, Warehouse] = {}
_warehouses_lock = threading.Lock()


def warehouse() -> Warehouse:
    """The process-wide handle for ``settings.WAREHOUSE_PATH`` (tests override the path)."""
    path = Path(settings.WAREHOUSE_PATH)
    with _warehouses_lock:
        handle = _warehouses.get(path)
        if handle is None:
            handle = _warehouses[path] = Warehouse(path)
        return handle


def cache_key(wkt: str, build_hash: str, updated_at: datetime | None) -> str:
    """Stable key for one area on one warehouse build with one set of definitions."""
    stamp = "" if updated_at is None else updated_at.isoformat()
    digest = hashlib.sha256(f"{wkt}\n{build_hash}\n{stamp}".encode()).hexdigest()
    return f"kpis:{digest}"


def district_refs() -> dict[str, DistrictRef]:
    """The catalogue as the resolver wants it (one query)."""
    return {d.slug: DistrictRef(d.slug, d.overture_id) for d in District.objects.all()}


def kpis(request: AreaRequest) -> dict[str, Any]:
    """The serialised response for one area request.

    Raises:
        InvalidAreaError: the area is unusable (422 at the view).
        WarehouseMissingError: ``make load-data`` has not run (503 at the view).
        RegistryMismatchError: code and database disagree on the KPI set (500: a deploy bug).
    """
    defs = definitions.load()
    districts = district_refs() if request.district is not None else {}
    handle = warehouse()
    with handle.cursor() as con:
        area = resolve(con, request, districts)
        key = cache_key(area.wkt, handle.info.build_hash, defs.updated_at)
        hit = cache.get(key)
        if hit is not None:
            return {**hit, "meta": {**hit["meta"], "cached": True}}
        response = engine.compute(con, area, defs.kpis)
    data: dict[str, Any] = KpiResponseSerializer(response).data
    cache.set(key, data)
    return data


def districts() -> list[dict[str, Any]]:
    """Every catalogue district with its outline, from the warehouse (cached per build)."""
    handle = warehouse()
    with handle.cursor() as con:
        key = f"districts:{handle.info.build_hash}"
        hit = cache.get(key)
        if hit is not None:
            return list(hit)
        rows = [
            {"slug": d.slug, "name": d.name, **warehouse_area.district_outline(con, d.overture_id)}
            for d in District.objects.all()
        ]
    data = list(DistrictSerializer(rows, many=True).data)
    cache.set(key, data)
    return data
