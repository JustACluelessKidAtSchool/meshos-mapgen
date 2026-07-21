"""Unit tests for Web Mercator tile math and coordinate generation."""

from meshos_mapgen.config import RegionConfig
from meshos_mapgen.presets import BoundingBox
from meshos_mapgen.tiles import (
    TileCoord,
    bbox_to_tile_range,
    count_tiles_for_region,
    generate_region_tiles,
    lat_to_tile_y,
    lon_to_tile_x,
)


def test_lon_lat_to_tile() -> None:
    # Null island (0, 0) at zoom 0
    assert lon_to_tile_x(0.0, 0) == 0
    assert lat_to_tile_y(0.0, 0) == 0

    # Boston approx (-71.05, 42.36) at zoom 10
    x = lon_to_tile_x(-71.05, 10)
    y = lat_to_tile_y(42.36, 10)
    assert x > 0 and x < 1024
    assert y > 0 and y < 1024


def test_bbox_to_tile_range() -> None:
    bbox = BoundingBox(west=-73.55, south=41.95, east=-71.55, north=42.90)
    x_min, x_max, y_min, y_max = bbox_to_tile_range(bbox, zoom=10)
    assert x_min <= x_max
    assert y_min <= y_max


def test_tile_coord_path() -> None:
    tc = TileCoord(z=18, x=75210, y=98432)
    assert tc.relative_path() == "18/75210/98432.png"


def test_count_and_generate_tiles() -> None:
    region = RegionConfig(name="western-massachusetts", zoom="10-11")
    count = count_tiles_for_region(region)
    tiles = list(generate_region_tiles(region))

    assert len(tiles) == count
    assert count > 0
    assert all(t.z in (10, 11) for t in tiles)
