"""Seed the KPI metadata from the Phase 3 registry (frozen here on purpose).

Literals, not an import of ``registry.py``: a migration must produce the same rows forever,
while the code moves on. Edits after this point happen in the admin or in a new migration.
"""

from django.db import migrations

ROWS = [
    {
        "key": "low_speed_street_share",
        "label": "Carriageway limited to 30 km/h or less",
        "definition": (
            "Share of carriageway length inside the area whose posted speed limit is 30 km/h "
            "or lower, over the carriageway length that has a mapped limit at all."
        ),
        "not_claim": (
            "A posted limit, not an observed speed. Carriageway without a mapped limit is "
            "excluded from both numerator and denominator, not assumed fast; the share "
            "excluded is shown alongside. Says nothing about enforcement, crashes or lane count."
        ),
        "bands": [
            {"label": "Mostly 50", "max": 40},
            {"label": "Mixed", "max": 70},
            {"label": "Calmed", "max": None},
        ],
        "source_kind": "citation",
        "source_label": "Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC",
        "source_url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969",
        "source_note": (
            "The 30 km/h threshold is the statutory urban limit for roads with one lane per "
            "direction since 11 May 2021. The band boundaries at 40 % and 70 % are chosen: "
            "the district reads 50.7 %, and the bands separate a superblock interior from a "
            "through-route corridor."
        ),
        "breakdown_note": "",
    },
    {
        "key": "crossing_density",
        "label": "Pedestrian crossings per km of carriageway",
        "definition": (
            "Mapped pedestrian crossing points inside the area per kilometre of carriageway "
            "inside the area."
        ),
        "not_claim": (
            "A crossing point carries no quality: signalised, raised, marked or lit are not "
            "known. High density does not mean safe crossing, and a pedestrianised area with "
            "no carriageway has nothing to cross and reads as no data, not as zero."
        ),
        "bands": [
            {"label": "Sparse", "max": 10},
            {"label": "Moderate", "max": 20},
            {"label": "Dense", "max": None},
        ],
        "source_kind": "chosen",
        "source_label": "Chosen: half and roughly the district mean",
        "source_url": "",
        "source_note": (
            "No standard I could verify prescribes crossings per kilometre. The district "
            "reads 22.6/km; bands at 10 and 20 make blocks below the district norm read as "
            "such."
        ),
        "breakdown_note": (
            "No breakdown: Overture carries no attributes on a crossing point to split by."
        ),
    },
    {
        "key": "pedestrian_network_share",
        "label": "Network length that is pedestrian-only",
        "definition": (
            "Share of all mapped network length inside the area that is pedestrian-only "
            "geometry (footways, pedestrian streets, steps, paths)."
        ),
        "not_claim": (
            "Not comparable across cities: Overture maps sidewalks here as separate geometry, "
            "which inflates pedestrian kilometres relative to places that map sidewalks as "
            "road attributes. Says nothing about sidewalk width, quality or continuity."
        ),
        "bands": [
            {"label": "Car-dominated", "max": 30},
            {"label": "Mixed", "max": 60},
            {"label": "Walking-first", "max": None},
        ],
        "source_kind": "chosen",
        "source_label": "Chosen: bands bracket the district figure",
        "source_url": "",
        "source_note": (
            "The district reads 52 %. Bands at 30 % and 60 % let pedestrianised streets and "
            "superblocks (higher) and through-route blocks (lower) separate."
        ),
        "breakdown_note": "",
    },
    {
        "key": "green_space_distance_p50",
        "label": "Median distance to a green space of at least 0.5 ha",
        "definition": (
            "Median straight-line distance from a building centroid inside the area to the "
            "nearest mapped green space of at least 0.5 ha, wherever that green space lies; "
            "the size floor and the 300 m band follow WHO Europe (2017)."
        ),
        "not_claim": (
            "Straight-line, not walking distance: a park across a railway reads as near. Only "
            "polygons Overture carries count, so interior courtyard gardens and pocket greens "
            "under 0.5 ha are ignored by design. Building centroids are not people."
        ),
        "bands": [
            {"label": "Within WHO rule of thumb", "max": 300},
            {"label": "Beyond", "max": 600},
            {"label": "Far", "max": None},
        ],
        "source_kind": "citation",
        "source_label": "WHO Europe, Urban green spaces: a brief for action (2017), p. 11",
        "source_url": "https://www.who.int/europe/publications/i/item/9789289052498",
        "source_note": (
            '"urban residents should be able to access public green spaces of at least '
            "0.5–1 hectare within 300 metres' linear distance (around 5 minutes' walk) of "
            'their homes." The 600 m boundary is chosen: double the WHO distance.'
        ),
        "breakdown_note": "",
    },
    {
        "key": "street_tree_density",
        "label": "Street trees per km of carriageway",
        "definition": (
            "Mapped individual trees inside the area per kilometre of carriageway inside the "
            "area."
        ),
        "not_claim": (
            "A shade and greenness proxy, not a safety measure. Canopy size, species and "
            "health are unknown; a sapling counts the same as a plane tree. Tree mapping is "
            "OSM-derived and can be uneven outside this district."
        ),
        "bands": [
            {"label": "Sparse", "max": 20},
            {"label": "Moderate", "max": 50},
            {"label": "Dense", "max": None},
        ],
        "source_kind": "chosen",
        "source_label": "Chosen: district mean and less than half of it",
        "source_url": "",
        "source_note": (
            "The district reads 55/km with every full 1 km cell between 752 and 2,001 trees."
        ),
        "breakdown_note": "No breakdown: Overture tree points carry no species, size or canopy.",
    },
]


def seed(apps, schema_editor):
    KpiDefinition = apps.get_model("kpis", "KpiDefinition")
    for row in ROWS:
        KpiDefinition.objects.update_or_create(key=row["key"], defaults=row)


def unseed(apps, schema_editor):
    KpiDefinition = apps.get_model("kpis", "KpiDefinition")
    KpiDefinition.objects.filter(key__in=[r["key"] for r in ROWS]).delete()


class Migration(migrations.Migration):
    dependencies = [("kpis", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
