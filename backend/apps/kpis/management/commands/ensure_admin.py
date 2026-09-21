"""Create the admin user from settings, idempotently.

``createsuperuser --noinput`` exits non-zero when the user already exists, which would break
the container's ``migrate && check && ensure_admin && runserver`` chain on every restart.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """``manage.py ensure_admin``."""

    help = "Create the admin superuser from ADMIN_USERNAME / ADMIN_PASSWORD if it is missing."

    def handle(self, *args: object, **options: object) -> None:
        """Create the user when absent; never touch an existing one."""
        user_model = get_user_model()
        username = settings.ADMIN_USERNAME
        if user_model.objects.filter(username=username).exists():
            self.stdout.write(f"admin user {username!r} present")
            return
        user_model.objects.create_superuser(username=username, password=settings.ADMIN_PASSWORD)
        self.stdout.write(f"created admin user {username!r}")
