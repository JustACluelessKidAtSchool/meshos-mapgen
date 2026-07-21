"""Unit tests for estimate engine."""

from pathlib import Path

from meshos_mapgen.config import MapGenConfig, RegionConfig
from meshos_mapgen.estimate import estimate_config


def test_estimate_config(tmp_path: Path) -> None:
    config = MapGenConfig(
        output=str(tmp_path / "tiles"),
        regions=[
            RegionConfig(name="western-massachusetts", zoom="5-6"),
        ],
    )
    est = estimate_config(config)

    assert len(est.regions) == 1
    assert est.total_tiles > 0
    assert est.missing_tiles == est.total_tiles
    assert est.total_bytes > 0
    assert est.format_bytes() != ""
    assert est.format_time() != ""
