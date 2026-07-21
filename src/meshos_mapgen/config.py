"""Configuration models and YAML parser using Pydantic."""

import os
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator

from meshos_mapgen.presets import PRESET_BOUNDING_BOXES, WESTERN_MASS_MAX_YAML, BoundingBox


class CustomBBox(BaseModel):
    """Custom geographic bounding box."""

    west: float
    south: float
    east: float
    north: float

    def to_preset(self) -> BoundingBox:
        """Convert to BoundingBox object."""
        return BoundingBox(
            west=self.west,
            south=self.south,
            east=self.east,
            north=self.north,
        )


class RegionConfig(BaseModel):
    """Configuration for a rendering region."""

    name: str
    zoom: str | int
    min_zoom: int = 0
    max_zoom: int = 0
    bbox: CustomBBox | list[float] | tuple[float, float, float, float] | None = None

    @model_validator(mode="after")
    def parse_zoom_and_bbox(self) -> Self:
        """Parse zoom range string/int into min_zoom and max_zoom, and validate bbox."""
        if isinstance(self.zoom, int):
            self.min_zoom = self.zoom
            self.max_zoom = self.zoom
        elif isinstance(self.zoom, str):
            zoom_str = self.zoom.strip()
            if "-" in zoom_str:
                parts = zoom_str.split("-")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    self.min_zoom = int(parts[0])
                    self.max_zoom = int(parts[1])
                else:
                    raise ValueError(f"Invalid zoom range format: '{self.zoom}'")
            elif zoom_str.isdigit():
                self.min_zoom = int(zoom_str)
                self.max_zoom = int(zoom_str)
            else:
                raise ValueError(f"Invalid zoom specification: '{self.zoom}'")
        else:
            raise ValueError(f"Zoom must be int or string, got {type(self.zoom)}")

        if self.min_zoom < 0 or self.max_zoom > 20 or self.min_zoom > self.max_zoom:
            raise ValueError(
                f"Zoom levels must be between 0 and 20 (min <= max). "
                f"Got min={self.min_zoom}, max={self.max_zoom}"
            )

        return self

    def get_bounding_box(self) -> BoundingBox:
        """Resolve bounding box from explicit bbox field or pre-defined preset."""
        if self.bbox is not None:
            if isinstance(self.bbox, CustomBBox):
                return self.bbox.to_preset()
            elif isinstance(self.bbox, (list, tuple)) and len(self.bbox) == 4:
                return BoundingBox(
                    west=float(self.bbox[0]),
                    south=float(self.bbox[1]),
                    east=float(self.bbox[2]),
                    north=float(self.bbox[3]),
                )
            else:
                raise ValueError(f"Invalid custom bbox for region '{self.name}': {self.bbox}")

        normalized_name = self.name.lower().replace("_", "-")
        if normalized_name in PRESET_BOUNDING_BOXES:
            return PRESET_BOUNDING_BOXES[normalized_name]

        raise ValueError(
            f"Unknown region preset '{self.name}' and no custom 'bbox' provided. "
            f"Available presets: {list(PRESET_BOUNDING_BOXES.keys())}"
        )


class MapGenConfig(BaseModel):
    """Main application configuration."""

    style: str = "osm-carto"
    output: str = "~/MeshOS-Tiles"
    threads: str | int = "auto"
    optimize_png: bool = True
    regions: list[RegionConfig] = Field(default_factory=list)

    def resolve_output_dir(self) -> Path:
        """Expand user path and return absolute Path object."""
        return Path(self.output).expanduser().resolve()

    def resolve_tiles_dir(self) -> Path:
        """Return path to tiles/ directory inside output folder."""
        return self.resolve_output_dir() / "tiles"

    def resolve_threads(self) -> int:
        """Resolve CPU thread count."""
        if isinstance(self.threads, int):
            return max(1, self.threads)

        if isinstance(self.threads, str) and self.threads.strip().lower() == "auto":
            cpu_count = os.cpu_count() or 4
            return max(1, cpu_count - 2)

        try:
            val = int(self.threads)
            return max(1, val)
        except ValueError:
            cpu_count = os.cpu_count() or 4
            return max(1, cpu_count - 2)

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> Self:
        """Load and parse MapGenConfig from a YAML file."""
        yaml_path = Path(path).expanduser().resolve()
        if not yaml_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls.model_validate(data)

    @classmethod
    def get_default_yaml_content(cls) -> str:
        """Return default YAML configuration content for western-mass-max profile."""
        return WESTERN_MASS_MAX_YAML
