"""KPI computation pins on a hand-checkable synthetic warehouse.

Each test sketches a few metres of geometry and asserts the exact number a person would
compute by hand. If someone changes a buffer, a class list, the clipping rule or swaps a
length function, these fail. Nothing here touches the network or the real extract.
"""

from __future__ import annotations

import pytest

from apps.areas.resolve import AreaRequest, InvalidAreaError, resolve
from apps.kpis import registry
from apps.kpis.engine import compute_with_connection
from apps.kpis.insights import generate
from tests.fixtures.synthetic import SyntheticWarehouse
from warehouse.kpi import run_kpi

APPROX = 1e-6  # the 4326 round trip of the fixture geometry is exact to well below this


@pytest.fixture
def wh() -> SyntheticWarehouse:
    return SyntheticWarehouse()


def kpi(
    wh: SyntheticWarehouse, key: str
) -> tuple[float | None, int, dict[str, float] | None, dict[str, float | None]]:
    """(value, sample_size, breakdown-by-key, context-by-key) for one KPI on the registered area."""
    row = run_kpi(wh.con, registry.BY_KEY[key].sql)
    breakdown = None if row.breakdown is None else {b.key: b.value for b in row.breakdown}
    return row.value, row.sample_size, breakdown, {c.key: c.value for c in row.context}


# --- low_speed_street_share ------------------------------------------------------------


def test_low_speed_share_is_length_weighted_over_mapped_carriageway(wh: SyntheticWarehouse) -> None:
    wh.segment(100, 100, 200, 100, speed=30)  # 100 m at 30
    wh.segment(100, 200, 200, 200, speed=50)  # 100 m at 50
    wh.segment(100, 300, 200, 300, speed=None)  # 100 m, no mapped limit: excluded both sides
    wh.segment(100, 400, 200, 400, cls="footway", speed=30)  # not carriageway: ignored
    wh.area(0, 0, 500, 500)

    value, n, breakdown, ctx = kpi(wh, "low_speed_street_share")
    assert value == pytest.approx(50.0, abs=APPROX)
    assert n == 2
    assert breakdown == pytest.approx(
        {"le20": 0.0, "le30": 0.1, "le50": 0.1, "gt50": 0.0, "none": 0.1}, abs=APPROX
    )
    assert ctx["limit_coverage"] == pytest.approx(100 * 200 / 300, abs=APPROX)
    assert ctx["carriageway_km"] == pytest.approx(0.3, abs=APPROX)


def test_partial_segment_contributes_its_clipped_length(wh: SyntheticWarehouse) -> None:
    wh.segment(0, 100, 100, 100, speed=30)  # 100 m at 30; the area covers x in [60, 500] -> 40 m
    wh.segment(100, 200, 200, 200, speed=50)  # 100 m at 50, fully inside
    wh.area(60, 0, 500, 500)

    value, n, _, ctx = kpi(wh, "low_speed_street_share")
    assert value == pytest.approx(100 * 40 / 140, abs=APPROX)
    assert n == 2
    assert ctx["mapped_km"] == pytest.approx(0.14, abs=APPROX)


# --- crossing_density ------------------------------------------------------------------


def test_crossing_density_is_points_in_area_per_clipped_carriageway_km(
    wh: SyntheticWarehouse,
) -> None:
    wh.segment(0, 100, 500, 100, speed=30)  # 500 m
    wh.segment(0, 200, 500, 200, speed=30)  # 500 m  -> 1 km carriageway
    for x in (50, 150, 250, 350, 450):
        wh.crossing(x, 100)
    wh.crossing(600, 100)  # outside the area
    wh.area(0, 0, 500, 500)

    value, n, breakdown, ctx = kpi(wh, "crossing_density")
    assert value == pytest.approx(5.0, abs=APPROX)
    assert n == 2
    assert breakdown is None
    assert ctx["crossings"] == 5


def test_crossing_density_is_null_without_carriageway(wh: SyntheticWarehouse) -> None:
    wh.segment(0, 100, 500, 100, cls="footway")  # pedestrian only: no carriageway to cross
    wh.crossing(50, 100)
    wh.area(0, 0, 500, 500)

    value, n, _, _ = kpi(wh, "crossing_density")
    assert value is None
    assert n == 0


# --- pedestrian_network_share ----------------------------------------------------------


def test_pedestrian_share_over_total_network_with_class_breakdown(wh: SyntheticWarehouse) -> None:
    wh.segment(0, 100, 100, 100, cls="footway")  # 100 m pedestrian
    wh.segment(0, 200, 100, 200, cls="residential", speed=30)  # 100 m carriageway
    wh.segment(0, 300, 200, 300, cls="cycleway")  # 200 m cycle: denominator only
    wh.area(0, 0, 500, 500)

    value, n, breakdown, ctx = kpi(wh, "pedestrian_network_share")
    assert value == pytest.approx(25.0, abs=APPROX)
    assert n == 3
    assert breakdown == pytest.approx(
        {"cycleway": 0.2, "footway": 0.1, "residential": 0.1}, abs=APPROX
    )
    assert ctx["network_km"] == pytest.approx(0.4, abs=APPROX)


# --- green_space_distance_p50 ----------------------------------------------------------


def test_green_distance_clips_population_but_searches_all_targets(wh: SyntheticWarehouse) -> None:
    """CLAUDE.md §8: buildings inside the area, targets anywhere -> finite p50, never null."""
    wh.building(100, 150)
    wh.building(100, 170)  # both 200 m from the park's western edge (x = 300)
    wh.green(300, 100, 400, 200)  # 100 x 100 m = 1 ha, outside the area, 200 m east
    wh.green(120, 140, 170, 190)  # 50 x 50 m = 0.25 ha, only 20 m away: below the WHO floor
    wh.area(0, 0, 200, 400)  # contains the two buildings and no qualifying green space

    value, n, breakdown, ctx = kpi(wh, "green_space_distance_p50")
    assert value is not None
    assert value == pytest.approx(200.0, abs=1e-3)  # (100,150) -> polygon edge at x=300 is 200 m
    assert n == 2
    assert breakdown == {"within_300": 2.0, "within_600": 0.0, "beyond_600": 0.0}
    assert ctx["targets"] == 1


def test_green_distance_beyond_district_still_counts(wh: SyntheticWarehouse) -> None:
    wh.building(1_950, 1_000)
    wh.green(2_100, 950, 2_300, 1_050)  # outside the 2 km district entirely
    wh.area(1_900, 900, 2_000, 1_100)

    value, n, _, _ = kpi(wh, "green_space_distance_p50")
    assert value == pytest.approx(150.0, abs=1e-3)
    assert n == 1


# --- street_tree_density ---------------------------------------------------------------


def test_tree_density_per_clipped_carriageway_km(wh: SyntheticWarehouse) -> None:
    wh.segment(0, 100, 1_000, 100, speed=30)  # 1 km, area covers x in [0, 500] -> 0.5 km
    for i in range(10):
        wh.tree(10 + i * 40, 90)  # 10 trees inside
    wh.tree(900, 90)  # outside
    wh.area(0, 0, 500, 500)

    value, n, breakdown, ctx = kpi(wh, "street_tree_density")
    assert value == pytest.approx(20.0, abs=APPROX)
    assert n == 1
    assert breakdown is None
    assert ctx["trees"] == 10


# --- contract, empty, invalid ----------------------------------------------------------


def test_empty_area_returns_null_values_and_zero_sample_size(wh: SyntheticWarehouse) -> None:
    wh.segment(1_500, 1_500, 1_600, 1_500, speed=30)  # far from the area
    wh.building(1_500, 1_600)
    area = wh.area(0, 0, 200, 200)

    response = compute_with_connection(wh.con, area, with_layers=True)
    for result in response.kpis:
        assert result.row.value is None, result.key
        assert result.row.sample_size == 0, result.key
        assert result.band is None
    assert all(len(layer.features) == 0 for layer in response.layers)
    assert any("none of the features" in s for s in response.insights)


@pytest.mark.parametrize(
    ("polygon", "reason"),
    [
        (  # bow-tie: self-intersecting
            [[0, 0], [100, 100], [100, 0], [0, 100], [0, 0]],
            "not valid",
        ),
        (  # 8 km x 8 km = 64 km2 > 50 km2 cap
            [[0, 0], [8_000, 0], [8_000, 8_000], [0, 8_000], [0, 0]],
            "maximum is 50",
        ),
        (  # entirely outside the 2 km district
            [[3_000, 3_000], [3_100, 3_000], [3_100, 3_100], [3_000, 3_100], [3_000, 3_000]],
            "does not touch",
        ),
    ],
)
def test_invalid_areas_are_refused(
    wh: SyntheticWarehouse, polygon: list[list[float]], reason: str
) -> None:
    from tests.fixtures.synthetic import X0, Y0

    coords = ", ".join(f"{X0 + x} {Y0 + y}" for x, y in polygon)
    geojson = wh.geojson(f"POLYGON(({coords}))")
    with pytest.raises(InvalidAreaError, match=reason):
        resolve(wh.con, AreaRequest(polygon=geojson))


def test_every_kpi_declares_what_it_does_not_claim_and_a_source() -> None:
    for definition in registry.KPIS:
        assert definition.not_claim.strip(), definition.key
        assert definition.sql.is_file(), definition.key
        assert all(layer.sql.is_file() for layer in definition.layers), definition.key
        assert definition.bands and definition.bands[-1].max is None, definition.key
        if definition.source.kind is registry.SourceKind.CITATION:
            assert definition.source.url, definition.key
        else:
            assert definition.source.note, definition.key


def test_band_assignment_uses_upper_bounds() -> None:
    low_speed = registry.LOW_SPEED_STREET_SHARE
    assert low_speed.band_for(39.9) == "Mostly 50"
    assert low_speed.band_for(40) == "Mostly 50"
    assert low_speed.band_for(69.9) == "Mixed"
    assert low_speed.band_for(100) == "Calmed"
    assert low_speed.band_for(None) is None


def test_two_areas_produce_different_insights(wh: SyntheticWarehouse) -> None:
    # Area A: calmed street with a footway, crossings, trees, park next door.
    wh.segment(0, 100, 500, 100, speed=30)
    wh.segment(0, 110, 500, 110, cls="footway")
    wh.building(100, 150)
    wh.green(0, 200, 100, 300)
    for x in range(0, 500, 20):
        wh.tree(x, 90)
        wh.crossing(x + 10, 100)
    # Area B: one 50 km/h street, no footway, no crossings, no trees, far from any park.
    wh.segment(1_000, 100, 1_500, 100, speed=50)
    wh.building(1_100, 150)

    a = compute_with_connection(wh.con, wh.area(0, 0, 600, 400), with_layers=False)
    b = compute_with_connection(wh.con, wh.area(1_000, 0, 1_600, 400), with_layers=False)

    assert a.insights and b.insights
    assert set(a.insights).isdisjoint(b.insights)
    assert all(any(ch.isdigit() for ch in s) for s in (*a.insights, *b.insights))
    assert generate(a.kpis, a.area) == list(a.insights)  # deterministic
