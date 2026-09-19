"""Development settings: local Docker Compose and the test suite.

Secrets fall back to throwaway defaults here on purpose. The Postgres password matches
the compose default and the secret key follows Django's own ``startproject`` convention
(``django-insecure-`` prefix). See README "Configuration" for why this does not violate
the no-hardcoded-secrets rule: these credentials only ever guard a local container.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = True

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-not-a-real-secret-change-in-prod",
)

ALLOWED_HOSTS = ["*"]

DATABASES["default"]["PASSWORD"] = env("POSTGRES_PASSWORD", default="urbview_dev")  # noqa: F405
