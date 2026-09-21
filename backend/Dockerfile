# Backend image: Django + DRF + DuckDB. Development-oriented (runserver, editable install);
# a production server is a deployment concern outside this take-home's scope.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so source edits do not invalidate the pip layer.
COPY pyproject.toml ./
RUN mkdir -p config apps warehouse pipeline \
    && pip install -e ".[dev]"

# Bake the DuckDB spatial extension into the image: no network needed at runtime, and the
# build itself fails early if PROJ/GEOS do not load on this base image (Phase 1 gate).
RUN python -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL spatial'); c.execute('LOAD spatial'); print('spatial ok', duckdb.__version__)"

COPY . .

EXPOSE 8000
# migrate, then refuse to serve if the KPI registry and the database disagree (kpis.E001),
# then make sure the admin login exists, then serve.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py check --database default && python manage.py ensure_admin && python manage.py runserver 0.0.0.0:8000"]
