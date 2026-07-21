"""Web Mercator tile coordinate calculations and tile coordinate generator."""

import math
from collections.abc import Generator
from typing import NamedTuple

from meshos_mapgen.config import MapGenConfig, RegionConfig
from meshos_mapgen.presets import BoundingBox


class TileCoord(NamedTuple):
    """XYZ Tile Coordinate representation."""

    z: int
    x: int
    y: int

    def relative_path(self) -> str:
        """Return relative path format: 'z/x/y.png'."""
        return f"{self.z}/{self.x}/{self.y}.png"


def lon_to_tile_x(lon: float, zoom: int) -> int:
    """Convert longitude in degrees to tile X coordinate."""
    n = 1 << zoom
    x = int((lon + 180.0) / 360.0 * n)
    return max(0, min(x, n - 1))


def lat_to_tile_y(lat: float, zoom: int) -> int:
    """Convert latitude in degrees to tile Y coordinate."""
    n = 1 << zoom
    lat = max(-85.05112878, min(85.05112878, lat))
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(y, n - 1))


def tile_x_to_lon(x: int, zoom: int) -> float:
    """Convert tile X coordinate to western boundary longitude."""
    n = 1 << zoom
    return x / n * 360.0 - 180.0


def tile_y_to_lat(y: int, zoom: int) -> float:
    """Convert tile Y coordinate to northern boundary latitude."""
    n = 1 << zoom
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return math.degrees(lat_rad)


def bbox_to_tile_range(bbox: BoundingBox, zoom: int) -> tuple[int, int, int, int]:
    """Calculate (x_min, x_max, y_min, y_max) tile range for a bounding box at zoom level."""
    x_min = lon_to_tile_x(bbox.west, zoom)
    x_max = lon_to_tile_x(bbox.east, zoom)

    # North maps to smaller y, South maps to larger y
    y_min = lat_to_tile_y(bbox.north, zoom)
    y_max = lat_to_tile_y(bbox.south, zoom)

    if x_min > x_max:
        x_min, x_max = x_max, x_min
    if y_min > y_max:
        y_min, y_max = y_max, y_min

    return (x_min, x_max, y_min, y_max)


def count_tiles_for_region(region: RegionConfig) -> int:
    """Calculate total number of tiles in a region across its zoom levels."""
    bbox = region.get_bounding_box()
    total = 0
    for z in range(region.min_zoom, region.max_zoom + 1):
        x_min, x_max, y_min, y_max = bbox_to_tile_range(bbox, z)
        total += (x_max - x_min + 1) * (y_max - y_min + 1)
    return total


def generate_region_tiles(region: RegionConfig) -> Generator[TileCoord, None, None]:
    """Yield all TileCoord objects for a region."""
    bbox = region.get_bounding_box()
    for z in range(region.min_zoom, region.max_zoom + 1):
        x_min, x_max, y_min, y_max = bbox_to_tile_range(bbox, z)
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                yield TileCoord(z=z, x=x, y=y)


def count_total_tiles_config(config: MapGenConfig) -> dict[str, int]:
    """Count tiles per region and total across config."""
    counts: dict[str, int] = {}
    total = 0
    for region in config.regions:
        c = count_tiles_for_region(region)
        counts[region.name] = c
        total += c
    counts["total"] = total
    return counts
