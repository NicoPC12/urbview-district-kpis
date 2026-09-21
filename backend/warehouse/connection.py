"""DuckDB access for the warehouse. No Django imports anywhere in this package.

One read-only connection per process, one *cursor* per request. A DuckDB cursor is a separate
client context on the same database instance: temp tables, ``SET VARIABLE`` values and temp
macros are private to it (verified in Phase 4 and pinned by ``test_concurrency.py``), so two
requests never see each other's ``area``. Opening the file costs ~140 ms; a cursor costs
nothing measurable.

The warehouse can be (re)built while the server runs — the documented setup is
``docker compose up`` *then* ``make load-data``. ``build.py`` writes a temp file and
``os.replace``s it, so :class:`Warehouse` detects a new file by ``stat`` and reopens under a
lock, after every in-flight cursor has finished; it never closes a connection under a cursor.

Tests use :func:`connect_memory` to get an empty warehouse with the production schema.
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import duckdb

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
QUERIES_DIR = Path(__file__).resolve().parent / "queries"
LAYERS_DIR = Path(__file__).resolve().parent / "layers"

DEG_CRS = "EPSG:4326"
M_CRS = "EPSG:25831"


class WarehouseMissingError(FileNotFoundError):
    """The warehouse file has not been built yet (``make load-data``)."""


@dataclass(frozen=True)
class WarehouseInfo:
    """Identity of the file currently open, read from its ``meta`` table."""

    build_hash: str
    """sha256 over every ``meta`` row: changes on every rebuild (``built_at``) and on any
    change of release or source parquet. Part of the response cache key."""
    overture_release: str


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


def read_info(con: duckdb.DuckDBPyConnection) -> WarehouseInfo:
    """Build hash and release of the warehouse behind ``con``."""
    rows = con.execute("SELECT key, value FROM meta ORDER BY key").fetchall()
    digest = hashlib.sha256()
    for key, value in rows:
        digest.update(f"{key}={value}\n".encode())
    release = next((str(v) for k, v in rows if k == "overture_release"), "")
    return WarehouseInfo(build_hash=digest.hexdigest(), overture_release=release)


class Warehouse:
    """Process-wide handle on one warehouse file: a shared connection, a cursor per request.

    Thread-safe. The file's ``(mtime, size)`` is checked on every :meth:`cursor` call; when it
    changes the connection is reopened once all in-flight cursors are released. DuckDB caches
    database instances per path inside a process, so the old connection must be closed
    *before* the new one opens or the new one would silently be the old instance.
    """

    def __init__(self, path: Path) -> None:
        """Bind to a path; nothing is opened until the first cursor."""
        self.path = path
        self._cv = threading.Condition()
        self._con: duckdb.DuckDBPyConnection | None = None
        self._info: WarehouseInfo | None = None
        self._stamp: tuple[int, int] | None = None
        self._in_flight = 0

    def _stat(self) -> tuple[int, int]:
        try:
            st = os.stat(self.path)
        except FileNotFoundError as exc:
            raise WarehouseMissingError(f"{self.path} not found — run `make load-data`") from exc
        return st.st_mtime_ns, st.st_size

    def _reopen(self, stamp: tuple[int, int]) -> None:
        """Swap connections. Caller holds the lock and has verified nothing is in flight."""
        if self._con is not None:
            self._con.close()
            self._con = None
        con = connect(self.path)
        self._info = read_info(con)
        self._con = con
        self._stamp = stamp

    @property
    def info(self) -> WarehouseInfo:
        """Identity of the currently open file (opens it if needed).

        Raises:
            WarehouseMissingError: the file does not exist.
        """
        with self.cursor():
            assert self._info is not None  # noqa: S101 - set by _reopen inside cursor()
            return self._info

    @contextmanager
    def cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """A private cursor on the current file, for exactly one request.

        Raises:
            WarehouseMissingError: the file does not exist (503 at the API).
        """
        with self._cv:
            while True:
                stamp = self._stat()
                if stamp == self._stamp and self._con is not None:
                    break
                if self._in_flight:
                    self._cv.wait(timeout=1.0)  # a request is still on the old file
                    continue
                self._reopen(stamp)
                break
            self._in_flight += 1
            con = self._con
        assert con is not None  # noqa: S101 - set under the lock above
        cur = con.cursor()
        try:
            yield cur
        finally:
            cur.close()
            with self._cv:
                self._in_flight -= 1
                self._cv.notify_all()


def transform_to_m(expr: str) -> str:
    """SQL fragment: 4326 → 25831 with the axis-order flag rule 9 requires."""
    return f"ST_Transform({expr}, '{DEG_CRS}', '{M_CRS}', always_xy := true)"


def transform_to_deg(expr: str) -> str:
    """SQL fragment: 25831 → 4326 with the axis-order flag rule 9 requires."""
    return f"ST_Transform({expr}, '{M_CRS}', '{DEG_CRS}', always_xy := true)"
