"""Unit tests for configuration models and presets."""

from pathlib import Path

import pytest

from meshos_mapgen.config import MapGenConfig, RegionConfig
from meshos_mapgen.presets import PRESET_BOUNDING_BOXES


def test_preset_bounding_boxes_exist() -> None:
    assert "western-massachusetts" in PRESET_BOUNDING_BOXES
    assert "massachusetts" in PRESET_BOUNDING_BOXES
    assert "new-england" in PRESET_BOUNDING_BOXES
    assert "southern-vermont" in PRESET_BOUNDING_BOXES
    assert "southern-new-hampshire" in PRESET_BOUNDING_BOXES

    wmass = PRESET_BOUNDING_BOXES["western-massachusetts"]
    assert wmass.west == -73.55
    assert wmass.south == 41.95
    assert wmass.east == -71.55
    assert wmass.north == 42.90


def test_region_config_zoom_parsing() -> None:
    reg1 = RegionConfig(name="massachusetts", zoom="13-17")
    assert reg1.min_zoom == 13
    assert reg1.max_zoom == 17

    reg2 = RegionConfig(name="western-massachusetts", zoom=18)
    assert reg2.min_zoom == 18
    assert reg2.max_zoom == 18

    with pytest.raises(ValueError):
        RegionConfig(name="invalid", zoom="25-10")


def test_mapgen_config_from_yaml(tmp_path: Path) -> None:
    yaml_content = """
style: osm-carto
output: ~/MeshOS-Tiles
threads: auto
optimize_png: true

regions:
  - name: western-massachusetts
    zoom: 18
"""
    yaml_file = tmp_path / "test_config.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    cfg = MapGenConfig.from_yaml_file(yaml_file)
    assert cfg.style == "osm-carto"
    assert len(cfg.regions) == 1
    assert cfg.regions[0].name == "western-massachusetts"
    assert cfg.regions[0].min_zoom == 18
    assert cfg.resolve_threads() >= 1
