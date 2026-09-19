"""Production settings.

Every secret is required: ``env("...")`` without a default raises
``ImproperlyConfigured`` at import time, so a misconfigured deployment fails to boot
rather than starting with a guessable key.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

DATABASES["default"]["PASSWORD"] = env("POSTGRES_PASSWORD")  # noqa: F405

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
