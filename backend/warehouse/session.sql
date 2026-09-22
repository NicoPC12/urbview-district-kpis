-- Per-request definitions shared by the KPI and layer SQL files. Loaded into every request
-- cursor by warehouse.area.register_area (temp objects are cursor-private), so a change here
-- needs no warehouse rebuild.

-- Which land_use (subtype, class) pairs count as PUBLIC green space for the WHO-based
-- distance KPI. WHO's sentence says "public green spaces"; NOTES.md lists what each class
-- holds in this extract. Parks and village greens are public by definition; `garden` here is
-- Barcelona's municipal "Jardins de …" (leisure=garden in OSM); `recreation_ground` is the
-- public outdoor-exercise ground. Pitches, stadiums, marinas, nurseries, meadows, farmyards
-- and unnamed managed grass are not public green space and are excluded.
CREATE OR REPLACE TEMP TABLE public_green_classes (subtype VARCHAR, class VARCHAR);
INSERT INTO public_green_classes VALUES
    ('park', 'park'),
    ('park', 'village_green'),
    ('horticulture', 'garden'),
    ('recreation', 'recreation_ground');
