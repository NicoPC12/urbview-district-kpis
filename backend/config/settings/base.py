"""Environment-independent Django settings.

Values that differ between environments come from the process environment via
``django-environ``. This module never reads secrets with a default: ``dev`` and ``prod``
decide what is required and what may fall back.
"""

from pathlib import Path

import environ

# backend/ — the directory containing manage.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Load a repo-root .env if present (local runs outside Docker). Compose passes real env
# vars, so the file is optional and never required for the containers to start.
environ.Env.read_env(str(BASE_DIR.parent / ".env"))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.areas",
    "apps.kpis",
]

MIDDLEWARE = [
    # GZip first so it wraps everything: the district response is ~MBs of GeoJSON.
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [  # the admin needs these three
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# ---------------------------------------------------------------------------
# Database — PostgreSQL via Django ORM only. No geometry lives here (CLAUDE.md §3).
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="urbview"),
        "USER": env("POSTGRES_USER", default="urbview"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Warehouse — the DuckDB file built by `make load-data`. Read-only at request time.
# ---------------------------------------------------------------------------
WAREHOUSE_PATH = Path(
    env("WAREHOUSE_PATH", default=str(BASE_DIR.parent / "data" / "warehouse.duckdb"))
)

# ---------------------------------------------------------------------------
# I18N — everything is English (CLAUDE.md §9)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Madrid"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"

# ---------------------------------------------------------------------------
# Response cache — keyed by sha256(area WKT + warehouse build hash + newest KpiDefinition
# edit), so it never needs clearing. Process-local: fine for one dev container, Redis is the
# production answer (README "Caching").
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,  # entries are invalidated by key, not by age
        "OPTIONS": {"MAX_ENTRIES": 200},
    }
}

# ---------------------------------------------------------------------------
# REST framework + OpenAPI
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    # Every error body is RFC 7807 problem details (apps.kpis.problems).
    "EXCEPTION_HANDLER": "apps.kpis.problems.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "UrbView API",
    "DESCRIPTION": "KPIs for a city district or a drawn polygon, computed from Overture Maps.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Name enums after their Python enum so openapi-typescript emits `SourceKind`, not
    # `KpisSourceKindEnum`-style noise.
    "ENUM_NAME_OVERRIDES": {
        "SourceKind": "apps.kpis.registry.SourceKind",
        "Denominator": "apps.kpis.registry.Denominator",
        "AreaSource": "apps.areas.resolve.AreaSource",
    },
}

# ---------------------------------------------------------------------------
# Logging — plain console; containers collect stdout
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
