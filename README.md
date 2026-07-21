# meshos-mapgen

[![CI](https://github.com/JustACluelessKidAtSchool/meshos-mapgen/actions/workflows/ci.yml/badge.svg)](https://github.com/JustACluelessKidAtSchool/meshos-mapgen/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Linux | macOS | Windows](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](INSTALLATION.md)

**`meshos-mapgen`** is a production-quality, cross-platform CLI application designed to generate offline **OpenStreetMap raster tiles** for **MeshCore MeshOS** running on the **LilyGO T-Deck**.

It automatically fetches Geofabrik OSM extracts, merges state PBF datasets, renders standard OpenStreetMap Carto XYZ PNG tiles inside a Docker container, losslessly optimizes PNGs with `oxipng`, and outputs a ready-to-use `tiles/` directory formatted specifically for your T-Deck micro SD card.

---

## Key Features

- **MeshOS Compatible**: Generates standard XYZ PNG tiles in `tiles/{zoom}/{x}/{y}.png` format expected by MeshCore MeshOS on LilyGO T-Deck.
- **Cross-Platform**: Full support for Linux (Ubuntu, Debian, Mint, Arch, Fedora), macOS, and Windows (via WSL2 / Docker Desktop).
- **Auto-Installer & Portable Fallbacks**: Automatically detects missing system tools (`osmium-tool`, `oxipng`) and prompts to install them via system package manager (`apt`, `brew`, `pacman`, `dnf`), or falls back seamlessly to Docker containers and native Python libraries.
- **Smart Downloads**: Auto-downloads Geofabrik extracts for New England states (MA, CT, RI, VT, NH, ME) with ETag / Last-Modified caching, HTTP Range resume, and SHA256 checksum verification.
- **Seamless Docker Integration**: Automatically handles dataset merging and OpenStreetMap Carto container rendering with zero manual Mapnik or PostGIS setup.
- **Layered Zoom & Regions**: Multi-layered rendering with bounding box presets (`western-mass-max`, `western-massachusetts`, `massachusetts`, `new-england`, `southern-vermont`, `southern-new-hampshire`) or custom bounding boxes.
- **Resumable & Efficient**: Skips existing valid PNG tiles and already-optimized files automatically if interrupted or re-run.
- **Lossless PNG Optimization**: Runs `oxipng` automatically to minimize SD card storage footprint while retaining 100% visual quality.
- **Rich Terminal UI**: Live resource monitoring (CPU usage %, disk space, remaining SD capacity, render speed, and ETA).

---

## Quick Start

### Installation

Install via `pipx` (recommended):

```bash
pipx install meshos-mapgen
```

Or install from source:

```bash
git clone https://github.com/JustACluelessKidAtSchool/meshos-mapgen.git
cd meshos-mapgen
pip install .
```

### Usage

1. **Initialize Configuration**:

```bash
meshos-mapgen init
```
Creates a default `config.yaml` using the built-in `western-mass-max` profile.

2. **Estimate Requirements**:

```bash
meshos-mapgen estimate config.yaml
```
Previews total tile counts, estimated disk space, and estimated render time without rendering.

3. **Build Maps**:

```bash
meshos-mapgen build config.yaml
```
Downloads extracts, merges PBF data, renders tiles, optimizes PNGs, and saves output to `~/MeshOS-Tiles/tiles/`.

4. **Copy to SD Card**:
Copy the generated `tiles/` directory directly to the root of your LilyGO T-Deck micro SD card.

---

## Configuration Example (`config.yaml`)

```yaml
style: osm-carto
output: ~/MeshOS-Tiles
threads: auto
optimize_png: true

regions:
  - name: new-england
    zoom: 5-12

  - name: massachusetts
    zoom: 13-16

  - name: western-massachusetts
    zoom: 17

  - name: southern-vermont
    zoom: 16-17

  - name: southern-new-hampshire
    zoom: 16-17
```

---

## Presets & Bounding Boxes

Pre-configured presets available for use in `config.yaml`:

- `western-massachusetts`: `[-73.55, 41.95, -71.55, 42.90]`
- `massachusetts`: `[-73.5081, 41.2379, -69.9284, 42.8868]`
- `new-england`: `[-73.7278, 40.9801, -66.9499, 47.4597]`
- `southern-vermont`: `[-73.44, 42.74, -72.45, 43.50]`
- `southern-new-hampshire`: `[-72.56, 42.70, -70.70, 43.50]`

---

## Documentation

- [Installation Guide](INSTALLATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Architecture & Design](ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)

---

## License

Distributed under the [MIT License](LICENSE).
