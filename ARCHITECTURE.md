# Architecture & System Design

`meshos-mapgen` is structured as a modular, asynchronous Python application that orchestrates data acquisition, dataset merging, Docker tile rendering, and PNG optimization.

---

## Architectural Diagram

```
                       ┌─────────────────────────┐
                       │   meshos-mapgen CLI     │
                       │       (Typer / Rich)    │
                       └────────────┬────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
 ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
 │  Geofabrik         │  │  Osmium PBF        │  │  OpenStreetMap     │
 │  Downloader        │  │  Merger            │  │  Carto Renderer    │
 │ (aiohttp + ETag)   │  │ (Host / Docker)    │  │ (Docker TileServ)  │
 └──────────┬─────────┘  └──────────┬─────────┘  └──────────┬─────────┘
            │                       │                       │
            ▼                       ▼                       ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │                     Output Tile Store (XYZ PNGs)                  │
 │                       tiles/{z}/{x}/{y}.png                        │
 └──────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │  oxipng Optimizer  │
                         │(Lossless Compress) │
                         └────────────────────┘
```

---

## Core Components

### 1. Configuration & Presets (`config.py`, `presets.py`)
- Reads YAML settings via Pydantic models.
- Provides standard geographic bounding box presets (`western-mass-max`, `new-england`, `massachusetts`, etc.).
- Converts zoom strings (`5-12`) into explicit numeric zoom levels.

### 2. Web Mercator Tile Engine (`tiles.py`)
- Implements standard Web Mercator math mapping (latitude, longitude, zoom) to XYZ tile grid indices `(z, x, y)`.
- Generates tile lists for bounding boxes across zoom ranges.

### 3. Geofabrik Downloader (`downloader.py`)
- Downloads `.osm.pbf` state extracts asynchronously using `aiohttp`.
- Performs ETag and Last-Modified checks to eliminate unnecessary re-downloads.
- Supports HTTP range resume and SHA256 / MD5 checksum verification.

### 4. Dataset Merger (`merger.py`)
- Combines state PBF files into a unified dataset.
- Prefers native `osmium` binary if available; automatically spins up `stefda/osmium-tool` Docker container otherwise.

### 5. Tile Renderer (`renderer.py`)
- Integrates with Docker daemon (`overv/openstreetmap-tile-server`).
- Caches imported PostgreSQL database in a persistent Docker volume (`meshos-tile-pgdata`).
- Fetches missing tiles concurrently via multi-threaded HTTP worker pool.
- Guarantees resumability by inspecting existing tile validity before rendering.

### 6. PNG Optimizer (`optimizer.py`)
- Losslessly compresses generated PNG tiles using `oxipng` (or Pillow fallback).
- Maintains `.optimized_manifest.json` to prevent re-optimizing unchanged files.

### 7. UI & Estimation (`ui.py`, `estimate.py`)
- Rich progress bars and live resource panels (CPU, disk usage, remaining SD capacity).
- Pre-calculates exact tile counts, storage footprints, and estimated render durations.
