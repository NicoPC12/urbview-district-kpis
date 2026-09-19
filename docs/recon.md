# Phase 0 reconnaissance — what Overture `2026-08-19.0` carries for l'Eixample

**Purpose.** Evidence for choosing the KPI set and for the walkthrough. Nothing in here is a
KPI; it is counts, schemas and distributions from the actual release, computed inside the
district polygon.

**How it was produced.** `python -m pipeline.recon` inside the backend container
([`backend/pipeline/recon.py`](../backend/pipeline/recon.py)), run on 2026-09-19. Part 1 below
is the script's output verbatim (`data/recon/recon.md`); Parts 2–4 are written by hand from
those numbers. Re-running the script regenerates Part 1 in ~10 s from the cached extract, or in
~13 min from S3 on a clean machine.

**Release.** `2026-08-19.0` — the latest listed in `s3://overturemaps-us-west-2/release/`
on 2026-09-19 (the one before it is `2026-07-22.0`). Pinned in
[`backend/pipeline/release.py`](../backend/pipeline/release.py).

**Method notes that matter for reading the tables.**
- Download filter: Barcelona-wide bbox `2.05, 41.32, 2.24, 41.47` pushed down on the `bbox`
  struct. Exact clipping afterwards with `ST_Intersects(feature, district)` — a feature is
  counted if any part of it touches the district. Lengths and areas marked *clipped* use
  `ST_Intersection`, so a segment half inside contributes half its length.
- Every metre is measured in EPSG:25831 with `always_xy := true` (CLAUDE.md rule 9).
- "Carriageway" in the answers means `subtype = 'road'` excluding
  `footway, steps, path, cycleway` (and `pedestrian` where stated): the length a vehicle can
  drive, which is the natural denominator for lamps, speed limits and crossings.
- Download timings are wall-clock from the first pull's file modification times.

---

## Part 1 — Script output (verbatim)


### download timings (bbox-filtered, seconds, from the first pull)

| type | seconds | mb |
|---|---|---|
| division_area | 34 | 17.10 |
| segment | 173 | 27.60 |
| connector | 30 | 12.30 |
| infrastructure | 24 | 15.50 |
| land_use | 25 | 5.40 |
| land | 53 | 18.10 |
| water | 25 | 4.20 |
| building | 372 | 29.60 |
| place | 28 | 16.60 |

### schema: division_area

| column | type |
|---|---|
| id | VARCHAR |
| geometry | GEOMETRY('OGC:CRS84') |
| country | VARCHAR |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| subtype | VARCHAR |
| admin_level | INTEGER |
| class | VARCHAR |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| is_land | BOOLEAN |
| is_territorial | BOOLEAN |
| region | VARCHAR |
| division_id | VARCHAR |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: segment

| column | type |
|---|---|
| id | VARCHAR |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| subtype | VARCHAR |
| class | VARCHAR |
| subclass | VARCHAR |
| subclass_rules | STRUCT("value" VARCHAR, "between" DOUBLE[])[] |
| connectors | STRUCT(connector_id VARCHAR, "at" DOUBLE)[] |
| road_surface | STRUCT("value" VARCHAR, "between" DOUBLE[])[] |
| road_flags | STRUCT("values" VARCHAR[], "between" DOUBLE[])[] |
| rail_flags | STRUCT("values" VARCHAR[], "between" DOUBLE[])[] |
| width_rules | STRUCT("value" DOUBLE, "between" DOUBLE[])[] |
| level_rules | STRUCT("value" INTEGER, "between" DOUBLE[])[] |
| access_restrictions | STRUCT(access_type VARCHAR, "when" STRUCT(during VARCHAR, heading VARCHAR, "using" VARCHAR[], recognized VARCHAR[], "mode" VARCHAR[], vehicle STRUCT(dimension VARCHAR, comparison VARCHAR, "value" DOUBLE, unit VARCHAR)[]), "between" DOUBLE[])[] |
| speed_limits | STRUCT(min_speed STRUCT("value" INTEGER, unit VARCHAR), max_speed STRUCT("value" INTEGER, unit VARCHAR), is_max_speed_variable BOOLEAN, "when" STRUCT(during VARCHAR, heading VARCHAR, "using" VARCHAR[], recognized VARCHAR[], "mode" VARCHAR[], vehicle STRUCT(dimension VARCHAR, comparison VARCHAR, "value" DOUBLE, unit VARCHAR)[]), "between" DOUBLE[])[] |
| prohibited_transitions | STRUCT("sequence" STRUCT(connector_id VARCHAR, segment_id VARCHAR)[], final_heading VARCHAR, "when" STRUCT(heading VARCHAR, during VARCHAR, "using" VARCHAR[], recognized VARCHAR[], "mode" VARCHAR[], vehicle STRUCT(dimension VARCHAR, comparison VARCHAR, "value" DOUBLE, unit VARCHAR)[]), "between" DOUBLE[])[] |
| routes | STRUCT("name" VARCHAR, network VARCHAR, "ref" VARCHAR, symbol VARCHAR, wikidata VARCHAR, "between" DOUBLE[])[] |
| destinations | STRUCT(labels STRUCT("value" VARCHAR, "type" VARCHAR)[], symbols VARCHAR[], from_connector_id VARCHAR, to_segment_id VARCHAR, to_connector_id VARCHAR, "when" STRUCT(heading VARCHAR), final_heading VARCHAR)[] |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| geometry | GEOMETRY('OGC:CRS84') |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: connector

| column | type |
|---|---|
| id | VARCHAR |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| geometry | GEOMETRY('OGC:CRS84') |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: infrastructure

| column | type |
|---|---|
| id | VARCHAR |
| geometry | GEOMETRY('OGC:CRS84') |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| level | INTEGER |
| wikidata | VARCHAR |
| source_tags | MAP(VARCHAR, VARCHAR) |
| subtype | VARCHAR |
| class | VARCHAR |
| height | DOUBLE |
| surface | VARCHAR |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: land_use

| column | type |
|---|---|
| id | VARCHAR |
| geometry | GEOMETRY('OGC:CRS84') |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| level | INTEGER |
| wikidata | VARCHAR |
| source_tags | MAP(VARCHAR, VARCHAR) |
| subtype | VARCHAR |
| class | VARCHAR |
| elevation | INTEGER |
| surface | VARCHAR |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: land

| column | type |
|---|---|
| id | VARCHAR |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| subtype | VARCHAR |
| class | VARCHAR |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| source_tags | MAP(VARCHAR, VARCHAR) |
| level | INTEGER |
| wikidata | VARCHAR |
| surface | VARCHAR |
| elevation | INTEGER |
| geometry | GEOMETRY('OGC:CRS84') |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: water

| column | type |
|---|---|
| id | VARCHAR |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| subtype | VARCHAR |
| class | VARCHAR |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| source_tags | MAP(VARCHAR, VARCHAR) |
| level | INTEGER |
| wikidata | VARCHAR |
| is_intermittent | BOOLEAN |
| is_salt | BOOLEAN |
| geometry | GEOMETRY('OGC:CRS84') |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: building

| column | type |
|---|---|
| id | VARCHAR |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| level | INTEGER |
| height | DOUBLE |
| min_height | DOUBLE |
| is_underground | BOOLEAN |
| num_floors | INTEGER |
| num_floors_underground | INTEGER |
| min_floor | INTEGER |
| subtype | VARCHAR |
| class | VARCHAR |
| facade_color | VARCHAR |
| facade_material | VARCHAR |
| roof_material | VARCHAR |
| roof_shape | VARCHAR |
| roof_direction | DOUBLE |
| roof_orientation | VARCHAR |
| roof_color | VARCHAR |
| roof_height | DOUBLE |
| geometry | GEOMETRY('OGC:CRS84') |
| has_parts | BOOLEAN |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### schema: place

| column | type |
|---|---|
| id | VARCHAR |
| geometry | GEOMETRY('OGC:CRS84') |
| categories | STRUCT("primary" VARCHAR, alternate VARCHAR[]) |
| confidence | DOUBLE |
| websites | VARCHAR[] |
| emails | VARCHAR[] |
| socials | VARCHAR[] |
| phones | VARCHAR[] |
| brand | STRUCT(wikidata VARCHAR, "names" STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[])) |
| addresses | STRUCT(freeform VARCHAR, locality VARCHAR, postcode VARCHAR, region VARCHAR, country VARCHAR)[] |
| names | STRUCT("primary" VARCHAR, common MAP(VARCHAR, VARCHAR), rules STRUCT(variant VARCHAR, "language" VARCHAR, perspectives STRUCT("mode" VARCHAR, countries VARCHAR[]), "value" VARCHAR, "between" DOUBLE[], side VARCHAR)[]) |
| sources | STRUCT(property VARCHAR, dataset VARCHAR, license VARCHAR, record_id VARCHAR, update_time VARCHAR, confidence DOUBLE, "between" DOUBLE[], provider VARCHAR, resource VARCHAR, "version" VARCHAR)[] |
| operating_status | VARCHAR |
| basic_category | VARCHAR |
| taxonomy | STRUCT("primary" VARCHAR, hierarchy VARCHAR[], alternates VARCHAR[]) |
| version | INTEGER |
| bbox | STRUCT(xmin DOUBLE, xmax DOUBLE, ymin DOUBLE, ymax DOUBLE) |
| theme | VARCHAR |
| type | VARCHAR |

### division_area subtypes in the Barcelona bbox

| subtype | n |
|---|---|
| microhood | 401 |
| neighborhood | 84 |
| locality | 22 |
| macrohood | 22 |
| country | 8 |
| region | 1 |
| county | 1 |

### district candidates (area in EPSG:25831)

| name | subtype | class | geometry_type | area_km2 | id |
|---|---|---|---|---|---|
| Ciutat Vella | macrohood | land | POLYGON | 4.23 | 9f2b29d0-b591-4122-a9f5-a24bfe8a4440 |
| Gràcia | macrohood | land | POLYGON | 4.20 | 287026ec-1950-42ba-9608-6cad4e459235 |
| l'Eixample | macrohood | land | POLYGON | 7.51 | 0d75cc75-2546-4a6d-9266-c07357c909b3 |

### district

- **name**: l'Eixample
- **id**: 0d75cc75-2546-4a6d-9266-c07357c909b3
- **geometry_type**: POLYGON
- **area_km2**: 7.51
- **vertices**: 718
- **valid**: 1
- **xmin**: 2.14
- **ymin**: 41.37
- **xmax**: 2.19
- **ymax**: 41.41

### row counts: Barcelona bbox vs inside district

| type | rows_in_bbox | rows_in_district |
|---|---|---|
| segment | 103,920 | 6,806 |
| connector | 152,977 | 11,354 |
| infrastructure | 151,891 | 10,328 |
| land_use | 17,099 | 1,519 |
| land | 128,331 | 9,202 |
| water | 4,948 | 52 |
| building | 131,412 | 8,397 |
| place | 90,246 | 20,934 |

### segment: by subtype

| subtype | n |
|---|---|
| road | 6,721 |
| rail | 85 |

### segment: by class (top 15) with clipped length km

| class | n | length_km_clipped |
|---|---|---|
| footway | 4,093 | 240.14 |
| residential | 531 | 52.06 |
| secondary | 435 | 35.89 |
| tertiary | 327 | 27.00 |
| cycleway | 323 | 69.07 |
| steps | 289 | 2.05 |
| service | 174 | 12.79 |
| living_street | 149 | 14.65 |
| primary | 147 | 13.84 |
| unknown | 128 | 14.53 |
| pedestrian | 122 | 6.60 |
| standard_gauge | 36 | 29.82 |
| subway | 32 | 40.15 |
| path | 11 | 0.31 |
| tram | 9 | 3.73 |

### segment: class x subclass (top 15)

| class | subclass | n |
|---|---|---|
| footway | sidewalk | 1,741 |
| footway | crosswalk | 1,283 |
| footway | — | 1,069 |
| residential | — | 531 |
| secondary | — | 415 |
| cycleway | — | 296 |
| steps | — | 289 |
| tertiary | — | 278 |
| living_street | — | 149 |
| primary | — | 141 |
| unknown | — | 128 |
| pedestrian | — | 122 |
| service | parking_aisle | 92 |
| service | — | 75 |
| tertiary | link | 49 |

### segment: nullness of the columns a walkability KPI would use

- **n**: 6,806
- **has_subclass**: 3,225
- **has_access_restrictions**: 2,239
- **has_road_surface**: 5,321
- **has_road_flags**: 435
- **has_speed_limits**: 1,571
- **has_width_rules**: 798
- **has_level_rules**: 400

### segment: access_restrictions — access_type x mode x heading (unnested, top 15)

| access_type | modes | heading | n |
|---|---|---|---|
| denied | — | backward | 1,763 |
| allowed | bicycle | — | 234 |
| allowed | — | — | 190 |
| denied | motor_vehicle | — | 149 |
| denied | — | — | 123 |
| denied | foot | — | 117 |
| designated | bicycle | — | 103 |
| allowed | foot | — | 73 |
| allowed | motor_vehicle | — | 66 |
| denied | bicycle | — | 61 |
| designated | foot | — | 54 |
| allowed | foot,bicycle | — | 50 |
| allowed | bicycle,bus | — | 40 |
| denied | foot,motor_vehicle | — | 22 |
| denied | bicycle,motor_vehicle | — | 19 |

### segment: road_flags values (unnested)

| flag | n |
|---|---|
| is_tunnel | 306 |
| is_indoor | 115 |
| is_link | 76 |
| is_bridge | 40 |
| is_abandoned | 14 |
| is_under_construction | 9 |
| is_covered | 3 |

### segment: sample of three access_restrictions payloads (as JSON)

| class | subclass | access_restrictions |
|---|---|---|
| pedestrian | — | [{"access_type":"denied","when":{"during":null,"heading":"backward","using":null,"recognized":null,"mode":null,"vehicle":null},"between":null},{"access_type":"designated","when":{"during":null,"heading":null,"using":null,"recognized":null,"mode":["bicycle"],"vehicle":null},"between":null},{"access_type":"allowed","when":{"during":null,"heading":null,"using":null,"recognized":null,"mode":["motor_vehicle"],"vehicle":null},"between":null}] |
| residential | — | [{"access_type":"denied","when":{"during":null,"heading":"backward","using":null,"recognized":null,"mode":null,"vehicle":null},"between":null}] |
| cycleway | — | [{"access_type":"denied","when":{"during":null,"heading":"backward","using":null,"recognized":null,"mode":null,"vehicle":null},"between":null}] |

### connector: degree distribution (segments in district referencing the connector)

| degree | n |
|---|---|
| 1 | 663 |
| 2 | 7,960 |
| 3 | 1,977 |
| 4+ | 754 |

### infrastructure: subtype x class (full cross-tab)

| subtype | class | n |
|---|---|---|
| barrier | kerb | 252 |
| barrier | wall | 144 |
| barrier | gate | 130 |
| barrier | fence | 123 |
| barrier | bollard | 55 |
| barrier | retaining_wall | 9 |
| barrier | lift_gate | 7 |
| barrier | barrier | 7 |
| barrier | handrail | 5 |
| barrier | entrance | 3 |
| barrier | planter | 2 |
| barrier | hedge | 2 |
| bridge | bridge | 37 |
| bridge | covered | 2 |
| communication | communication_tower | 4 |
| emergency | fire_hydrant | 120 |
| pedestrian | bench | 675 |
| pedestrian | vending_machine | 136 |
| pedestrian | artwork | 109 |
| pedestrian | information | 64 |
| pedestrian | post_box | 63 |
| pedestrian | atm | 59 |
| pedestrian | toilets | 38 |
| pedestrian | viewpoint | 3 |
| power | substation | 3 |
| power | generator | 2 |
| tower | bell_tower | 21 |
| tower | lighting | 1 |
| transit | bicycle_parking | 786 |
| transit | stop_position | 391 |
| transit | bus_stop | 287 |
| transit | parking | 160 |
| transit | bicycle_rental | 126 |
| transit | parking_entrance | 92 |
| transit | platform | 68 |
| transit | motorcycle_parking | 64 |
| transit | subway_station | 27 |
| transit | parking_space | 3 |
| transit | railway_station | 3 |
| transit | bus_station | 1 |
| transportation | crossing | 3,624 |
| transportation | traffic_signals | 1,382 |
| transportation | street_lamp | 236 |
| transportation | give_way | 28 |
| transportation | charging_station | 26 |
| transportation | stop | 5 |
| utility | water_tower | 1 |
| utility | reservoir_covered | 1 |
| waste_management | recycling | 387 |
| waste_management | waste_basket | 284 |
| waste_management | waste_disposal | 51 |
| water | drinking_water | 212 |
| water | fountain | 7 |

### infrastructure: geometry types

| gt | n |
|---|---|
| POINT | 9,720 |
| LINESTRING | 356 |
| POLYGON | 251 |
| MULTIPOLYGON | 1 |

### infrastructure: street lamps as PLAN.md named them (subtype='utility', class='street_lamp')

0

### infrastructure: street lamps under any subtype (class='street_lamp')

| subtype | gt | n |
|---|---|---|
| transportation | POINT | 236 |

### infrastructure: anything transit-looking (subtype/class ILIKE bus|tram|subway|metro|station|platform|stop|rail)

| subtype | class | n |
|---|---|---|
| transportation | crossing | 3,624 |
| transportation | traffic_signals | 1,382 |
| transit | bicycle_parking | 786 |
| transit | stop_position | 391 |
| transit | bus_stop | 287 |
| transportation | street_lamp | 236 |
| transit | parking | 160 |
| transit | bicycle_rental | 126 |
| transit | parking_entrance | 92 |
| transit | platform | 68 |
| transit | motorcycle_parking | 64 |
| transportation | give_way | 28 |
| transit | subway_station | 27 |
| transportation | charging_station | 26 |
| barrier | handrail | 5 |
| transportation | stop | 5 |
| transit | parking_space | 3 |
| power | substation | 3 |
| transit | railway_station | 3 |
| transit | bus_station | 1 |

### land_use: by subtype x class with clipped area km2

| subtype | class | gt | n | area_km2_clipped |
|---|---|---|---|---|
| residential | residential | POLYGON | 88 | 1.37 |
| park | park | POLYGON | 55 | 0.30 |
| pedestrian | pedestrian | POLYGON | 206 | 0.25 |
| developed | commercial | POLYGON | 4 | 0.09 |
| developed | retail | POLYGON | 4 | 0.09 |
| education | school | POLYGON | 27 | 0.08 |
| horticulture | garden | POLYGON | 797 | 0.08 |
| managed | grass | POLYGON | 175 | 0.07 |
| education | education | POLYGON | 1 | 0.06 |
| construction | construction | POLYGON | 11 | 0.03 |
| pedestrian | plaza | POLYGON | 9 | 0.03 |
| medical | hospital | POLYGON | 1 | 0.03 |
| recreation | pitch | POLYGON | 29 | 0.02 |
| education | university | POLYGON | 1 | 0.02 |
| religious | religious | POLYGON | 1 | 0.02 |
| developed | industrial | POLYGON | 1 | 0.01 |
| recreation | playground | POLYGON | 44 | 0.01 |
| agriculture | meadow | POLYGON | 27 | 0.01 |
| recreation | recreation_ground | POLYGON | 2 | 0.01 |
| park | dog_park | POLYGON | 8 | 0.01 |
| construction | greenfield | POLYGON | 3 | 0.00 |
| developed | brownfield | POLYGON | 3 | 0.00 |
| education | kindergarten | POLYGON | 5 | 0.00 |
| horticulture | allotments | POLYGON | 2 | 0.00 |
| horticulture | plant_nursery | POLYGON | 1 | 0.00 |
| horticulture | flowerbed | POLYGON | 11 | 0.00 |
| transportation | railway | POLYGON | 1 | 0.00 |
| transportation | traffic_island | POLYGON | 2 | 0.00 |

### land: by subtype x class with clipped area km2

| subtype | class | gt | n | area_km2_clipped |
|---|---|---|---|---|
| land | land | POLYGON | 1 | 7.51 |
| physical | peninsula | MULTIPOLYGON | 1 | 7.51 |
| shrub | heath | POLYGON | 175 | 0.02 |
| forest | wood | POLYGON | 3 | 0.00 |
| rock | shingle | POLYGON | 1 | 0.00 |
| forest | forest | POLYGON | 1 | 0.00 |
| shrub | scrub | POLYGON | 2 | 0.00 |
| tree | tree | POINT | 8,880 | 0.00 |
| tree | tree_row | LINESTRING | 138 | 0.00 |

### water: by subtype x class with clipped area km2

| subtype | class | gt | n | area_km2_clipped |
|---|---|---|---|---|
| human_made | swimming_pool | POLYGON | 20 | 0.00 |
| stream | stream | LINESTRING | 12 | 0.00 |
| reservoir | basin | POLYGON | 6 | 0.00 |
| human_made | reflecting_pool | POLYGON | 5 | 0.00 |
| water | water | POLYGON | 4 | 0.00 |
| pond | pond | POLYGON | 3 | 0.00 |
| reservoir | reservoir | POLYGON | 2 | 0.00 |

### building: totals and attribute coverage

- **n**: 8,397
- **has_height**: 796
- **has_num_floors**: 4,227
- **has_class**: 7,307
- **has_subtype**: 7,328
- **footprint_km2_clipped**: 3.92

### building: by subtype (top 15)

| subtype | n |
|---|---|
| residential | 6,669 |
| — | 1,069 |
| commercial | 435 |
| civic | 94 |
| education | 52 |
| industrial | 26 |
| outbuilding | 19 |
| religious | 14 |
| entertainment | 6 |
| medical | 5 |
| service | 4 |
| transportation | 3 |
| agricultural | 1 |

### place: top 20 primary categories

| category | n |
|---|---|
| — | 834 |
| professional_services | 559 |
| hotel | 403 |
| restaurant | 397 |
| beauty_salon | 349 |
| community_services_non_profits | 337 |
| bar | 329 |
| lawyer | 328 |
| grocery_store | 328 |
| tapas_bar | 321 |
| clothing_store | 316 |
| spas | 310 |
| real_estate_service | 248 |
| hair_salon | 231 |
| party_and_event_planning | 231 |
| advertising_agency | 215 |
| spanish_restaurant | 209 |
| shopping | 200 |
| travel_services | 194 |
| cafe | 192 |

### place: confidence distribution

| confidence_band | n |
|---|---|
| 0.5-0.7 | 3,050 |
| 0.7-0.9 | 6,303 |
| <0.5 | 5,046 |
| >=0.9 | 6,535 |

### place: transit-looking categories (category ILIKE bus|tram|metro|subway|train|transit|transport|station)

| category | n |
|---|---|
| business_management_services | 70 |
| transportation | 43 |
| fitness_trainer | 29 |
| business_to_business | 26 |
| business_manufacturing_and_supply | 26 |
| train_station | 24 |
| bus_station | 23 |
| business_advertising | 19 |
| gas_station | 18 |
| radio_station | 11 |
| business_consulting | 10 |
| ev_charging_station | 8 |
| international_business_and_trade_services | 6 |
| metro_station | 6 |
| environmental_and_ecological_services_for_businesses | 6 |
| bus_tours | 4 |
| public_transportation | 4 |
| dog_trainer | 3 |
| business_schools | 3 |
| abuse_and_addiction_treatment | 3 |
| business_office_supplies_and_stationery | 2 |
| boat_rental_and_training | 2 |
| medical_transportation | 2 |
| business_banking_service | 2 |
| cards_and_stationery_store | 1 |
| business_law | 1 |
| domestic_business_and_trade_organizations | 1 |

### Q1 lamps: count, nearest-neighbour distance (m), lamps per km of road

- **lamps**: 236
- **with_neighbour_within_500m**: 235
- **median_nn_m**: 11.62
- **p25_nn_m**: 9.66
- **p75_nn_m**: 15.60
- **p90_nn_m**: 23.58
- **carriageway_km_excl_footway_cycleway**: 166.94
- **lamps_per_carriageway_km**: 1.41
- **mean_m_of_carriageway_per_lamp**: 707.35

### Q1 lamps: per 1 km grid cell summary (EPSG:25831 cells; 'mostly inside' = >0.9 km2 in district)

- **cells**: 17
- **cells_mostly_inside**: 4
- **min_lamps**: 0
- **median_lamps**: 2.00
- **max_lamps**: 80
- **cells_with_zero_lamps**: 4
- **min_mostly_inside**: 0
- **median_mostly_inside**: 14.50
- **max_mostly_inside**: 73

### Q1 lamps: per-cell detail (cx, cy are EPSG:25831 km indices)

| cx | cy | km2_in_district | lamps | road_km_all_classes |
|---|---|---|---|---|
| 428 | 4,580 | 0.06 | 1 | 5.19 |
| 428 | 4,581 | 0.64 | 1 | 39.95 |
| 428 | 4,582 | 0.49 | 1 | 30.39 |
| 429 | 4,580 | 0.27 | 2 | 19.31 |
| 429 | 4,581 | 1.00 | 0 | 58.90 |
| 429 | 4,582 | 0.98 | 73 | 53.24 |
| 429 | 4,583 | 0.09 | 22 | 7.88 |
| 430 | 4,580 | 0.08 | 3 | 5.83 |
| 430 | 4,581 | 0.12 | 0 | 9.64 |
| 430 | 4,582 | 0.94 | 2 | 59.09 |
| 430 | 4,583 | 0.74 | 80 | 51.26 |
| 430 | 4,584 | 0.21 | 6 | 13.52 |
| 431 | 4,582 | 0.47 | 1 | 28.33 |
| 431 | 4,583 | 0.99 | 27 | 67.33 |
| 431 | 4,584 | 0.40 | 17 | 25.81 |
| 432 | 4,582 | 0.00 | 0 | 0.24 |
| 432 | 4,583 | 0.02 | 0 | 2.25 |

### Q2 transit: totals

- **infrastructure rows matching the loose transit pattern**: 7,317
- **infrastructure boarding places (subtype='transit', class in stop classes)**: 777
- **place rows matching the loose transit pattern**: 353
- **segment rows with subtype='rail'**: 85

### Q2 transit: boarding places by class and geometry type

| class | gt | n |
|---|---|---|
| stop_position | POINT | 391 |
| bus_stop | POINT | 287 |
| platform | POLYGON | 61 |
| subway_station | POINT | 27 |
| platform | LINESTRING | 5 |
| railway_station | POINT | 3 |
| platform | POINT | 2 |
| bus_station | POLYGON | 1 |

### Q2 transit: building-centroid distance (m) to nearest bus_stop / subway_station (feasibility of a distance KPI and where its thresholds would bite)

- **buildings**: 8,397
- **p50_any_stop_m**: 79.41
- **p90_any_stop_m**: 143.63
- **p50_bus_m**: 83.31
- **p50_subway_m**: 264.72
- **pct_within_300m**: 100.00
- **pct_within_500m**: 100.00

### Q3 pedestrian: road segments by class — clipped km, and segments with an access rule that denies foot explicitly, denies unconditionally, or is only a one-way rule

| class | n | length_km | n_foot_denied | n_denied_unconditionally | n_one_way_only |
|---|---|---|---|---|---|
| footway | 4,093 | 240.14 | 0 | 22 | 1 |
| cycleway | 323 | 69.07 | 77 | 8 | 143 |
| residential | 531 | 52.06 | 2 | 9 | 522 |
| secondary | 435 | 35.89 | 4 | 1 | 418 |
| tertiary | 327 | 27.00 | 0 | 3 | 306 |
| living_street | 149 | 14.65 | 0 | 3 | 126 |
| primary | 147 | 13.84 | 51 | 1 | 144 |
| service | 174 | 12.79 | 3 | 23 | 80 |
| pedestrian | 122 | 6.60 | 0 | 1 | 17 |
| unknown | 120 | 4.11 | 0 | 1 | 1 |
| steps | 289 | 2.05 | 0 | 15 | 0 |
| path | 11 | 0.31 | 3 | 0 | 0 |

### Q4 land-use coverage and the shares a green/water KPI would produce

- **district_km2**: 7.51
- **land_use_union_km2**: 2.23
- **land_use_coverage_pct**: 29.67
- **green_land_use_union_km2 (park/horticulture/managed/recreation/agriculture)**: 0.44
- **green_land_use_pct**: 5.87
- **land_vegetation_polygons_km2 (forest/shrub/grass/tree)**: 0.02
- **water_union_km2**: 0.01
- **water_pct**: 0.10
- **building_footprint_union_km2**: 3.89
- **building_footprint_pct**: 51.76

### Q5 trees (base/land, subtype='tree'): count, per km of carriageway, per 1 km cell

- **trees**: 8,880
- **trees_per_carriageway_km**: 53.19
- **tree_rows**: 138
- **min_per_full_cell**: 752
- **median_per_full_cell**: 978.50
- **max_per_full_cell**: 2,001

### Q6 speed limits: carriageway km by posted max speed (first speed_limits rule, km/h)

| band | unit | segments | km |
|---|---|---|---|
| 31-50 | km/h | 786 | 70.31 |
| 21-30 | km/h | 596 | 54.95 |
| no limit mapped | — | 340 | 17.62 |
| <=20 | km/h | 161 | 17.46 |

### Q6 speed limits: share of carriageway km with a mapped limit, by class

| class | n | with_limit | pct_with_limit |
|---|---|---|---|
| residential | 531 | 495 | 93.20 |
| secondary | 435 | 431 | 99.10 |
| tertiary | 327 | 314 | 96.00 |
| service | 174 | 21 | 12.10 |
| living_street | 149 | 135 | 90.60 |
| primary | 147 | 146 | 99.30 |
| unknown | 120 | 1 | 0.80 |

### Q7 crossings and signals: infrastructure points per km of carriageway

- **carriageway_km**: 160.34
- **crossings**: 3,624
- **crossings_per_km**: 22.60
- **traffic_signals**: 1,382
- **signals_per_km**: 8.62
- **crossings_as_points**: 3,624

### total recon seconds

9.00

---

## Part 2 — What the schema actually looks like (vs. what CLAUDE.md / PLAN.md assumed)

Columns named in the planning documents, checked against the real `DESCRIBE`:

| Assumed | Reality in `2026-08-19.0` |
|---|---|
| `division_area.subtype = 'borough'` or `'neighborhood'` for districts | Barcelona's ten districts are **`subtype = 'macrohood'`** (22 macrohoods in the bbox, incl. Badalona's "Districte I–VI"). `neighborhood` (84) and `microhood` (401) are the barris and sub-barris. There is no `borough` subtype in this bbox. |
| `infrastructure` lamps under `subtype='utility', class='street_lamp'` | **Does not exist** (0 rows). Lamps are **`subtype='transportation', class='street_lamp'`** (236 POINTs). `utility` holds only `reservoir_covered` and `water_tower`. |
| "transit stops in `places`/`infrastructure`" | Both, but only `infrastructure` is usable: **`subtype='transit'`** with classes `bus_stop` (287), `stop_position` (391), `platform` (68), `subway_station` (27), `railway_station` (3), `bus_station` (1). `places` has `bus_station` 23, `train_station` 24, `metro_station` 6, `public_transportation` 4 — a POI list, not the stop network. |
| segment `class`/`subclass` | Present. `class` is the OSM-style highway class (`footway`, `residential`, `secondary`, …, plus rail classes `subway`, `standard_gauge`, `tram`). `subclass` is populated for 47 % of rows: `sidewalk`, `crosswalk`, `link`, `parking_aisle`, `driveway`. |
| "access restrictions" | `access_restrictions` = `STRUCT(access_type, when STRUCT(during, heading, using, recognized, mode[], vehicle[]), between[])[]`, present on 33 % of segments. **The dominant entry is a one-way rule** (`denied` + `heading='backward'`, mode null: 522 of 531 residential segments with a rule). Mode-specific rules are rarer: `denied foot` 117 entries, `allowed foot` 73, `designated foot` 54. |
| "the road struct" | There is **no `road` struct**. Its former contents are top-level columns: `road_surface`, `road_flags`, `speed_limits`, `width_rules`, `level_rules`, `prohibited_transitions`, `access_restrictions`, `routes`, `destinations`. |
| place categories | `categories.primary` (VARCHAR) + `categories.alternate` (VARCHAR[]). 20,934 places in the district, 834 with no category. `confidence` is populated (24 % below 0.5). |
| `connector` linkage | `segment.connectors` is `STRUCT(connector_id, at)[]`; the connector row itself has no back-reference, so degree is computed by unnesting segments. |
| building `height` | Exists but populated on **9.5 %** of buildings; `num_floors` on 50 %. |

Also confirmed: `geometry` comes in as `GEOMETRY('OGC:CRS84')`; `bbox` is a `STRUCT(xmin, xmax, ymin, ymax)` on every type; `theme`/`type` hive columns are added by `hive_partitioning = 1`.

---

## Part 3 — The district

- **`l'Eixample` is present** as `subtype='macrohood'`, `class='land'`, a valid single **POLYGON** with 718 vertices, id `0d75cc75-2546-4a6d-9266-c07357c909b3`.
- Area in EPSG:25831: **7.508 km²** (the brief's own figure is 7.46 km²; the 0.6 % difference is the boundary source, not the projection).
- Bbox: `2.14, 41.37 – 2.19, 41.41`.
- Fallbacks, in case they are ever needed: Gràcia 4.20 km², Ciutat Vella 4.23 km², both valid POLYGONs under the same subtype. **No hardcoded bbox is needed.**

---

## Part 4 — The questions that decide the KPI set

### Q1. Lamps

- **236** street lamps in 7.5 km² (`subtype='transportation', class='street_lamp'`, all POINTs).
- **Median nearest-neighbour distance: 11.6 m** (p25 9.7, p75 15.6, p90 23.6). 235 of 236 have a neighbour within 500 m. That is the spacing of lamps *along one mapped street*, not across the district.
- **Coverage is concentrated, not even.** 17 1-km cells touch the district; of the 4 cells that are >90 % inside it, lamp counts are **0, 2, 27, 73** (median 14.5). Two cells (`429/4582`, `430/4583`) hold 153 of the 236 lamps (65 %). Cell `429/4581` has 58.9 km of road and **zero** lamps.
- Per carriageway kilometre (here including the `pedestrian` class, 166.9 km): **1.41 lamps/km**, i.e. **one lamp per 707 m** of street. The KPI as specified uses a 25 m buffer; at the observed density a "lit street share" would read single digits everywhere except the two mapped streets.
- **Conclusion:** Overture (via OSM) carries a *sample* of Eixample's lamps — the ones a handful of mappers surveyed street by street. A lit-street KPI computed on it measures **mapping effort, not lighting**. That is a legitimate finding under the one-source rule, and a strong walkthrough slide, but it cannot be presented as a lighting metric.

### Q2. Transit

- **Stops exist, in `infrastructure`, and are dense**: 777 boarding places (`subtype='transit'`, stop classes), of which 287 `bus_stop` and 27 `subway_station` POINTs; 68 `platform` (mostly POLYGON); 391 `stop_position` (points on the track/road, one per stopping vehicle position — these duplicate bus stops and should not be counted as stops).
- Building-centroid distance to the nearest `bus_stop`/`subway_station`: **p50 = 79 m, p90 = 144 m**; to a subway station alone p50 = 265 m. **100 % of the 8,397 buildings are within 300 m** of a stop.
- **Conclusion:** computable and clean, but in this district the metric is **saturated**. Any polygon a reviewer draws will read 60–150 m to the nearest stop; bands at 300/500 m would never change colour. The honest uses are either (a) keep it as the required *distance* KPI and set bands that discriminate at 50/100/150 m (chosen, not cited), or (b) reframe as **stop density per km²** (a *density* KPI, which does vary block by block).

### Q3. Pedestrian access

- **A walkable / non-walkable split is derivable, and it is almost entirely class-driven.** `access_restrictions` adds little: explicit `denied foot` rules hit 77 cycleways, 51 primary-class segments and a handful of others — 140 of 6,721 road segments. Unconditional denials (no `when` at all) are 87 segments, mostly `service`, `footway` and `steps` (private access). Everything else flagged `denied` is a one-way rule.
- Lengths (clipped, `subtype='road'`): footway 240.1 km (of which sidewalk 1,741 segments, crosswalk 1,283), pedestrian 6.6, steps 2.1, path 0.3 → **249 km of pedestrian-only network** against 160 km of carriageway and 69 km of cycleway. Total road-subtype length ≈ 479 km.
- **Conclusion:** two defensible formulations. *"Share of network length open to pedestrians"* = (all classes minus explicit/unconditional foot denials) / total ≈ 97 % — computable but nearly constant. *"Share of network length that is pedestrian-only infrastructure"* = (footway+pedestrian+steps+path) / total ≈ **52 %** — computable, varies with superblocks and pedestrianised streets, and says something a reviewer can verify on foot. Either way the sidewalk data is there: 1,741 sidewalk segments is real coverage.

### Q4. Land use coverage

- `land_use` polygons cover **2.23 km² = 29.7 %** of the district. Residential alone is 1.37 km² (61 % of what is mapped). Building footprints cover **51.8 %** (union, clipped).
- Green (`park`, `horticulture`, `managed`, `recreation`, `agriculture` subtypes, unioned): **0.44 km² = 5.9 %**. Water: 0.01 km² = **0.1 %** (swimming pools, basins, a reflecting pool — Eixample has no natural water).
- `base/land` vegetation *polygons* add only 0.02 km²; `land` is otherwise the two district-covering `land`/`peninsula` polygons and **8,880 tree POINTs** (see surprises).
- **Conclusion:** a **land-use *mix*** KPI (entropy over `land_use` classes) would be computed on the 30 % of the district that happens to have a polygon, dominated by one class — it measures mapping coverage, not the city. A **green share** KPI is different: green polygons are the *positive* class, and their absence in a built-up block is real (the footprint union confirms the block is buildings). Green share is computable and honest with the caveat "polygons Overture carries"; the "+ water" half of the candidate contributes nothing here and should be dropped from the name.

### Surprises (things not asked about)

1. **Trees.** `base/land` carries **8,880 individual street trees as POINTs** plus 138 `tree_row` LINESTRINGs — **53 trees per carriageway km**, and every fully-inside 1-km cell has 752–2,001 of them (median 979). This is the densest, most evenly mapped point layer in the district by a wide margin, and a shade/greenness proxy that varies street by street.
2. **Speed limits.** `speed_limits` is populated on **89 % of carriageway km** (residential 93 %, secondary 99 %, primary 99 %; only `service` and `unknown` are blank). Of the 142.7 km with a limit: **50.7 % is ≤ 30 km/h** (54.9 km at 21–30, 17.5 km at ≤ 20), 49.3 % at 31–50, nothing above 50. This is the only layer in the extract that is directly a *road-safety* attribute, and its threshold has an obvious external anchor (30 km/h for streets where people walk).
3. **Crossings and signals.** `infrastructure` has **3,624 `crossing` POINTs (22.6 per carriageway km)** and **1,382 `traffic_signals` (8.6 per km)**. Together with 1,283 `crosswalk` footway segments this is a rich pedestrian-safety layer that the plan never considered.
4. **Places are rich but noisy**: 20,934 POIs in 7.5 km² (2,790 per km²), 24 % with confidence < 0.5, 4 % uncategorised. Usable for a diversity index of *activity*, not of land use.
5. **Buildings are usable as a denominator, not as a height source**: 8,397 footprints, 3.9 km² clipped, 87 % with a subtype (79 % residential) — but height on 9.5 % only.
6. **Connectors are not junctions.** 7,960 of 11,354 connectors have degree 2 (they split a segment where an attribute changes) and 663 have degree 1 (dead ends / district-edge cuts). Junctions in the intuitive sense are **degree ≥ 3: 2,731**, i.e. **364 per km²**. A junction-density KPI must filter on degree, and degree must be computed from the segments inside the polygon.
7. **The one-way trap.** The single most common `access_restrictions` entry (`denied`, no mode, `heading='backward'`) is a one-way rule. Any query that reads `access_type = 'denied'` as "closed" will call 80 % of Eixample's residential streets inaccessible.
8. **Download cost:** 12 min 45 s for the nine types over the Barcelona bbox from S3 (`building` 6.2 min, `segment` 2.9 min); 147 MB on disk. This confirms the Phase 2 plan of a prepared extract for `make load-data` — pulling from S3 alone eats most of the 15-minute budget.

---

## Part 5 — Recommendation

Marks: **GREEN** the data supports the KPI as intended; **AMBER** computable, but the caveat is large enough to belong in the KPI's `not_claim`; **RED** not computable as intended from this release.

| Candidate (PLAN.md) | Mark | The number that decides it | Strongest honest caveat |
|---|---|---|---|
| `lit_street_share` — street length within *r* m of a lamp | **RED** as a lighting metric; **AMBER** as "mapped-lamp coverage" | 236 lamps; 1 per 707 m of carriageway; 65 % of them in two 1-km cells; a full cell with 59 km of road has 0 | The value measures where OSM mappers surveyed lamps, not where light is. Cannot be shown as lighting. |
| `junction_density` — junctions per km² | **GREEN** | 2,731 connectors with degree ≥ 3 → 364 / km²; always computable | Degree counts *mapped* segments; footway-heavy mapping inflates junctions where sidewalks are drawn as separate ways. Say which classes count. |
| `walkable_network_share` — share of network length open to pedestrians | **AMBER** as "open to pedestrians" (≈ 97 %, nearly constant); **GREEN** if reframed as **pedestrian-only network share** | 249 km footway/pedestrian/steps/path of 479 km total = 52 %; 1,741 sidewalk segments | Sidewalk mapping completeness varies; a low share may mean sidewalks are not drawn, not that they do not exist. |
| `green_water_share` — share of area that is park/green/water | **GREEN** as **green share**, water dropped from the name | Green union 0.44 km² = 5.9 %; water 0.1 %; land_use covers 29.7 % but building footprints cover 51.8 %, so gaps are mostly real | Only polygons Overture carries; private courtyard gardens (Eixample's interior patios) are largely absent. |
| `land_use_mix` — entropy over land_use / place categories | **RED** over `land_use` (30 % coverage, one class = 61 % of it); **AMBER** over `places` | 2.23 km² mapped; 20,934 places, 24 % low-confidence | Over places it is a POI-diversity index, sensitive to Overture's category taxonomy and confidence filter, not a land-use measure. |
| `transit_distance_p50` — median building distance to nearest stop | **AMBER** | p50 79 m, p90 144 m, 100 % ≤ 300 m — saturated; 287 bus stops + 27 subway stations, clean POINTs | Every polygon reads "well served"; bands must sit at 50/100/150 m (chosen) to show any variation. Distance counts stops outside the drawn polygon, which is correct but must be stated. |

New candidates the data argues for (not in PLAN.md):

| Candidate | Mark | Number | Caveat |
|---|---|---|---|
| `low_speed_street_share` — share of carriageway length with a posted limit ≤ 30 km/h | **GREEN** | 89 % of carriageway km has a limit; 50.7 % of that is ≤ 30 | Posted limit is not observed speed; the unmapped 11 % (service, unknown) must be excluded from the denominator and said so. |
| `crossing_density` — pedestrian crossings per km of carriageway | **GREEN** | 3,624 crossing points, 22.6 / km; 1,382 signals | A crossing point says nothing about its quality (signalised, raised, lit). |
| `street_tree_density` — trees per km of carriageway | **GREEN** | 8,880 points, 53 / km, 752–2,001 per full 1-km cell | Trees are a shade/greenness proxy, not a safety measure; canopy size unknown. |

### Proposed set — four plus one stretch

The rubric wants at least one share, one density and one distance, and the brief says three well-argued KPIs beat five thin ones. Proposal, in the order I would build them:

1. **`low_speed_street_share`** (share) — the only KPI here that is *about* safety rather than adjacent to it, with an anchor for its threshold that is a policy rather than a guess. Caveat: posted, not observed.
2. **`crossing_density`** (density, per km of carriageway) — pedestrian infrastructure, rich and evenly mapped; pairs naturally with #1 in the insights ("30 km/h streets with few crossings").
3. **`pedestrian_network_share`** (share, footway+pedestrian+steps+path over all road-subtype length) — the walkability KPI reframed so it varies; the superblock vs. through-route story shows up in it.
4. **`transit_stop_distance_p50`** (distance) — keeps the distance requirement, is clean and cheap, and its saturation *is* the finding ("in Eixample nobody is far from a bus"); bands chosen at 50/100/150 m and labelled as chosen.
5. **Stretch: `street_tree_density`** (density) — cheapest to add, evenly mapped, and the most visually striking layer on the map (8,880 points).

**Why not `lit_street_share`:** it was the plan's headline KPI, and the data says it cannot be shown as lighting. I would rather spend one walkthrough slide on *why it was rejected* — 236 lamps, two mapped streets, the per-cell table above — than ship a number that reads as "this street is dark". If you want it kept as the "coverage gap as a finding" KPI, it should be named `mapped_lamp_coverage` and its `not_claim` has to be the first sentence on the card.

**Why not `junction_density`:** GREEN and always computable, but of the GREEN candidates it is the one that says least to a safety reader, and its "junction" needs a degree filter that will be argued about. Keep as the fallback if any of 1–3 hits a Phase 3 problem.

**Green share** is a close call for slot 5 against trees; trees win on evenness (no full cell below 752) and on map impact, green share wins on being a *share*. Either is a one-SQL-file swap later.

Denominators used above, per CLAUDE.md rule 2: carriageway length (KPIs 1, 2, stretch), total road-subtype length (3), building count (4), district/polygon area (green share). All legal.
