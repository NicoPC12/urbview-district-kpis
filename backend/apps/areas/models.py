"""The district catalogue: which slugs the API accepts and which warehouse row each names."""

from __future__ import annotations

from django.db import models


class District(models.Model):
    """A district the warehouse holds. ``overture_id`` joins to the warehouse ``district`` row."""

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    overture_id = models.CharField(
        max_length=64, unique=True, help_text="Overture division_area GERS id."
    )

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        """Slug, for the admin."""
        return self.slug
