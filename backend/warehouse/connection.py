"""DuckDB connection factory for the warehouse. No Django imports anywhere in this package.

The warehouse file is opened read-only per request: DuckDB connections are cheap to open
and are not safe to share across threads, so a connection per request is the simplest
correct model at this scale. Tests use :func:`connect_memory` to get an empty warehouse with
the production schema and fill it with hand-checkable rows.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
QUERIES_DIR = Path(__file__).resolve().parent / "queries"
LAYERS_DIR = Path(__file__).resolve().parent / "layers"

DEG_CRS = "EPSG:4326"
M_CRS = "EPSG:25831"


class WarehouseMissingError(FileNotFoundError):
    """The warehouse file has not been built yet (``make load-data``)."""


def _configure(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    con.execute("LOAD spatial")
    # Requests are small and concurrent; keep one process from monopolising the box.
    con.execute("SET threads = 4")
    con.execute("SET memory_limit = '1GB'")
    return con


def connect(path: Path, *, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open the warehouse file with the spatial extension loaded.

    Raises:
        WarehouseMissingError: when ``path`` does not exist, so the API can answer 503 with a
            message that names the command to run rather than a DuckDB stack trace.
    """
    if not path.is_file():
        raise WarehouseMissingError(f"{path} not found — run `make load-data`")
    return _configure(duckdb.connect(str(path), read_only=read_only))


def connect_memory() -> duckdb.DuckDBPyConnection:
    """Empty in-memory warehouse with the production schema, for tests and fixtures."""
    con = _configure(duckdb.connect())
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    return con


def transform_to_m(expr: str) -> str:
    """SQL fragment: 4326 → 25831 with the axis-order flag rule 9 requires."""
    return f"ST_Transform({expr}, '{DEG_CRS}', '{M_CRS}', always_xy := true)"


def transform_to_deg(expr: str) -> str:
    """SQL fragment: 25831 → 4326 with the axis-order flag rule 9 requires."""
    return f"ST_Transform({expr}, '{M_CRS}', '{DEG_CRS}', always_xy := true)"
