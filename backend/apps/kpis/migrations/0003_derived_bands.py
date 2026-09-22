"""Replace the chosen band boundaries with ones derived from the district's own distribution.

Method (pipeline/derive_bands.py, re-runnable): 250 m grid over the district in EPSG:25831,
each KPI computed per cell with the production SQL, cells with < 0.5 km of denominator
dropped (chosen), cutoffs = 33rd / 67th percentiles rounded to two significant figures.
Values as of Overture 2026-08-19.0 — see docs/derived_bands.json and NOTES.md.

Also carried here because they change what a reader must know: the pedestrian KPI now
excludes sidewalk and crosswalk geometry, and the green KPI counts public classes only.
"""

from django.db import migrations
from django.utils import timezone

DERIVED_NOTE = (
    "Bands are the 33rd and 67th percentiles of this KPI over 156 cells of 250 m covering "
    "Eixample (cells with under 0.5 km of denominator dropped; cutoffs rounded to two "
    "significant figures). They are relative to Eixample's own distribution, not an absolute "
    "standard. Method: backend/pipeline/derive_bands.py."
)

ROWS = {
    "low_speed_street_share": {
        "bands": [
            {"label": "Lower third", "max": 42},
            {"label": "Middle third", "max": 60},
            {"label": "Upper third", "max": None},
        ],
        "source_kind": "derived",
        "source_label": (
            "30 km/h: Real Decreto 970/2020 (BOE-A-2020-13969), art. 50 RGC; bands derived "
            "from Eixample's 250 m cells (P33 / P67)"
        ),
        "source_url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2020-13969",
        "source_note": (
            "The 30 km/h threshold is the statutory urban limit for roads with one lane per "
            "direction since 11 May 2021 (art. 50.1 RGC: 20 km/h single-platform streets, "
            "30 km/h one lane per direction, 50 km/h two or more). " + DERIVED_NOTE
        ),
        "not_claim": (
            "A posted limit, not an observed speed. Carriageway without a mapped limit is "
            "excluded from both numerator and denominator, not assumed fast; the share "
            "excluded is shown alongside. Says nothing about enforcement, crashes or lane "
            "count. Bands are relative to Eixample's own distribution, not an absolute "
            "standard."
        ),
    },
    "crossing_density": {
        "bands": [
            {"label": "Lower third", "max": 19},
            {"label": "Middle third", "max": 26},
            {"label": "Upper third", "max": None},
        ],
        "source_kind": "derived",
        "source_label": "Derived from Eixample's 250 m cells (P33 / P67)",
        "source_url": "",
        "source_note": (
            "No standard I could verify prescribes crossings per kilometre. " + DERIVED_NOTE
        ),
        "not_claim": (
            "A crossing point carries no quality: signalised, raised, marked or lit are not "
            "known. High density does not mean safe crossing, and a pedestrianised area with "
            "no carriageway has nothing to cross and reads as no data, not as zero. In "
            "shared-space or living streets, fewer marked crossings can mean the whole street "
            "has become crossable; a low reading there is not a deficit. Bands are relative to "
            "Eixample's own distribution, not an absolute standard."
        ),
    },
    "pedestrian_network_share": {
        "label": "Street network that is pedestrian-only (sidewalks excluded)",
        "definition": (
            "Share of the mapped street network length inside the area that is pedestrian-only "
            "geometry — pedestrian streets, footways, steps and paths — with sidewalk and "
            "crosswalk geometry excluded from both sides."
        ),
        "bands": [
            {"label": "Lower third", "max": 14},
            {"label": "Middle third", "max": 24},
            {"label": "Upper third", "max": None},
        ],
        "source_kind": "derived",
        "source_label": "Derived from Eixample's 250 m cells (P33 / P67)",
        "source_url": "",
        "source_note": (
            "Sidewalks are excluded because Overture maps only about half of Barcelona's "
            "sidewalks as separate lines (mapped sidewalk km per carriageway km ranges from "
            "0.7 to 1.5 across cells, median 1.1): with them in, the KPI measured mapping "
            "coverage, not the street. " + DERIVED_NOTE
        ),
        "not_claim": (
            "Street space given over to walking, not sidewalk provision: sidewalks and "
            "crosswalks are deliberately excluded because their mapping is incomplete. Says "
            "nothing about sidewalk width, quality or continuity. Bands are relative to "
            "Eixample's own distribution, not an absolute standard."
        ),
    },
    "street_tree_density": {
        "bands": [
            {"label": "Lower third", "max": 20},
            {"label": "Middle third", "max": 69},
            {"label": "Upper third", "max": None},
        ],
        "source_kind": "derived",
        "source_label": "Derived from Eixample's 250 m cells (P33 / P67)",
        "source_url": "",
        "source_note": DERIVED_NOTE,
        "not_claim": (
            "A shade and greenness proxy, not a safety measure. Canopy size, species and "
            "health are unknown; a sapling counts the same as a plane tree. Tree mapping is "
            "OSM-derived and can be uneven outside this district. Bands are relative to "
            "Eixample's own distribution, not an absolute standard."
        ),
    },
    "green_space_distance_p50": {
        "label": "Median distance to a public green space of at least 0.5 ha",
        "definition": (
            "Median straight-line distance from a building centroid inside the area to the "
            "nearest mapped public green space of at least 0.5 ha — parks, village greens, "
            "municipal gardens and recreation grounds — wherever that green space lies; the "
            "size floor and the 300 m band follow WHO Europe (2017)."
        ),
        "not_claim": (
            "Straight-line, not walking distance: a park across a railway reads as near. Only "
            "polygons Overture carries count, so interior courtyard gardens and pocket greens "
            "under 0.5 ha are ignored by design; pitches, stadiums, marinas and nurseries are "
            "excluded as not public green space. Linear street greening — tree-lined avenues "
            "and green axes such as Consell de Cent — is invisible to this KPI by design: it "
            "measures distance to green *areas* of at least 0.5 ha. Building centroids are not "
            "people."
        ),
    },
}


def apply(apps, schema_editor):
    KpiDefinition = apps.get_model("kpis", "KpiDefinition")
    for key, fields in ROWS.items():
        # update() skips auto_now; the timestamp is part of the response cache key.
        KpiDefinition.objects.filter(key=key).update(updated_at=timezone.now(), **fields)


class Migration(migrations.Migration):
    dependencies = [("kpis", "0002_seed_kpi_definitions")]
    # No reverse: the 0002 values are documented history, and reverting bands silently would
    # put chosen numbers back under a "derived" label.
    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
