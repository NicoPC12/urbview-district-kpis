"""Seed the one district the warehouse holds (Overture 2026-08-19.0 division_area id)."""

from django.db import migrations

ROWS = [
    {
        "slug": "eixample",
        "name": "Eixample",
        "overture_id": "0d75cc75-2546-4a6d-9266-c07357c909b3",
    }
]


def seed(apps, schema_editor):
    District = apps.get_model("areas", "District")
    for row in ROWS:
        District.objects.update_or_create(slug=row["slug"], defaults=row)


def unseed(apps, schema_editor):
    District = apps.get_model("areas", "District")
    District.objects.filter(slug__in=[r["slug"] for r in ROWS]).delete()


class Migration(migrations.Migration):
    dependencies = [("areas", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
