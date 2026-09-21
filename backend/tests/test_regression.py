"""Pin every KPI on the real district to two decimals.

Skipped when the warehouse has not been built (`make load-data`), so the suite stays green
on a data-less checkout; with data present, any change in the pipeline, the SQL or the
Overture release shows up as a diff here. Values as of Overture 2026-08-19.0.
"""

from __future__ import annotations

import pytest
from django.conf import settings

from apps.areas.resolve import AreaRequest
from apps.kpis.engine import compute

EXPECTED: dict[str, tuple[float, int]] = {
    # key: (value to 2 dp, sample_size)
    "low_speed_street_share": (50.73, 1435),
    "crossing_density": (22.60, 1754),
    "pedestrian_network_share": (52.06, 6585),
    "green_space_distance_p50": (362.03, 8397),
    "street_tree_density": (55.38, 1754),
}

pytestmark = pytest.mark.skipif(
    not settings.WAREHOUSE_PATH.is_file(), reason="warehouse not built (make load-data)"
)


def test_district_kpis_pinned_to_two_decimals() -> None:
    response = compute(settings.WAREHOUSE_PATH, AreaRequest(district="eixample"), with_layers=False)
    assert response.area.km2 == pytest.approx(7.508, abs=5e-4)
    assert response.meta.overture_release == "2026-08-19.0"
    actual = {k.key: (round(k.row.value or 0.0, 2), k.row.sample_size) for k in response.kpis}
    assert actual == EXPECTED
