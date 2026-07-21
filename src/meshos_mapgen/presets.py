"""Preset definitions for regions, bounding boxes, and default profiles."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class BoundingBox:
    """Geographic bounding box defined by WGS84 coordinates."""

    west: float
    south: float
    east: float
    north: float

    def to_tuple(self) -> tuple[float, float, float, float]:
        """Return (west, south, east, north)."""
        return (self.west, self.south, self.east, self.north)


# Predefined bounding boxes for supported presets
PRESET_BOUNDING_BOXES: Final[dict[str, BoundingBox]] = {
    "western-massachusetts": BoundingBox(
        west=-73.55,
        south=41.95,
        east=-71.55,
        north=42.90,
    ),
    "massachusetts": BoundingBox(
        west=-73.5081,
        south=41.2379,
        east=-69.9284,
        north=42.8868,
    ),
    "new-england": BoundingBox(
        west=-73.7278,
        south=40.9801,
        east=-66.9499,
        north=47.4597,
    ),
    "southern-vermont": BoundingBox(
        west=-73.44,
        south=42.74,
        east=-72.45,
        north=43.50,
    ),
    "southern-new-hampshire": BoundingBox(
        west=-72.56,
        south=42.70,
        east=-70.70,
        north=43.50,
    ),
}

# Geofabrik US state download names mapping
GEOFABRIK_STATES: Final[dict[str, str]] = {
    "massachusetts": "massachusetts",
    "connecticut": "connecticut",
    "rhode_island": "rhode-island",
    "rhode-island": "rhode-island",
    "vermont": "vermont",
    "new_hampshire": "new-hampshire",
    "new-hampshire": "new-hampshire",
    "maine": "maine",
}

DEFAULT_GEOFABRIK_BASE_URL: Final[str] = (
    "https://download.geofabrik.de/north-america/us"
)

WESTERN_MASS_MAX_YAML: Final[str] = (
    "# meshos-mapgen default configuration profile: western-mass-max\n"
    "style: osm-carto\n"
    "output: ~/MeshOS-Tiles\n"
    "threads: auto\n"
    "optimize_png: true\n\n"
    "regions:\n"
    "  - name: new-england\n"
    "    zoom: 5-12\n\n"
    "  - name: massachusetts\n"
    "    zoom: 13-17\n\n"
    "  - name: western-massachusetts\n"
    "    zoom: 18\n\n"
    "  - name: southern-vermont\n"
    "    zoom: 16-17\n\n"
    "  - name: southern-new-hampshire\n"
    "    zoom: 16-17\n"
)
