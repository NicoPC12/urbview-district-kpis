-- Warehouse schema. The single definition used by pipeline/build.py (real data) and by the
-- test fixtures (synthetic, hand-checkable data), so a KPI query is tested against exactly the
-- columns it runs on in production.
--
-- Every table carries geom (EPSG:4326, for serving GeoJSON) and geom_m (EPSG:25831, for every
-- metre). R-tree indexes go on geom_m: every KPI predicate is ST_Intersects(geom_m, <area>).

CREATE TABLE district (
    id       VARCHAR PRIMARY KEY,
    name     VARCHAR NOT NULL,
    geom     GEOMETRY NOT NULL,
    geom_m   GEOMETRY NOT NULL,
    area_m2  DOUBLE   NOT NULL
);

-- Road segments (Overture subtype = 'road'; rail is never loaded). Flags are precomputed so
-- the KPI SQL filters on booleans rather than re-deriving class semantics per request.
CREATE TABLE segments (
    id               VARCHAR PRIMARY KEY,     -- Overture GERS id
    name             VARCHAR,
    class            VARCHAR NOT NULL,
    subclass         VARCHAR,
    is_carriageway   BOOLEAN NOT NULL,        -- class not in footway/steps/path/cycleway/pedestrian
    is_pedestrian    BOOLEAN NOT NULL,        -- class in footway/pedestrian/steps/path
    max_speed_kmh    INTEGER,                 -- posted limit, NULL when none is mapped
    has_speed_limit  BOOLEAN NOT NULL,
    length_m         DOUBLE  NOT NULL,        -- whole-segment length in EPSG:25831
    geom             GEOMETRY NOT NULL,
    geom_m           GEOMETRY NOT NULL
);

CREATE TABLE crossings (
    id       VARCHAR PRIMARY KEY,
    geom     GEOMETRY NOT NULL,
    geom_m   GEOMETRY NOT NULL
);

-- Green land_use polygons within 1.5 km of the district bbox (not clipped to the district:
-- a nearest-neighbour target may lie outside it). is_who_size = area >= 0.5 ha.
CREATE TABLE green_spaces (
    id           VARCHAR PRIMARY KEY,
    name         VARCHAR,
    subtype      VARCHAR NOT NULL,
    class        VARCHAR,
    area_m2      DOUBLE  NOT NULL,
    is_who_size  BOOLEAN NOT NULL,
    geom         GEOMETRY NOT NULL,
    geom_m       GEOMETRY NOT NULL
);

-- Building centroids: the population for distance KPIs.
CREATE TABLE buildings (
    id       VARCHAR PRIMARY KEY,
    subtype  VARCHAR,
    class    VARCHAR,
    geom     GEOMETRY NOT NULL,
    geom_m   GEOMETRY NOT NULL
);

CREATE TABLE trees (
    id       VARCHAR PRIMARY KEY,
    geom     GEOMETRY NOT NULL,
    geom_m   GEOMETRY NOT NULL
);

CREATE TABLE meta (
    key    VARCHAR PRIMARY KEY,
    value  VARCHAR
);

CREATE INDEX segments_geom_m_rtree      ON segments     USING RTREE (geom_m);
CREATE INDEX crossings_geom_m_rtree     ON crossings    USING RTREE (geom_m);
CREATE INDEX green_spaces_geom_m_rtree  ON green_spaces USING RTREE (geom_m);
CREATE INDEX buildings_geom_m_rtree     ON buildings    USING RTREE (geom_m);
CREATE INDEX trees_geom_m_rtree         ON trees        USING RTREE (geom_m);
