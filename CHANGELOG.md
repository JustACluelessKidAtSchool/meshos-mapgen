# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-20

### Added
- Initial production-quality release of `meshos-mapgen`.
- Automated downloading of Geofabrik OpenStreetMap extracts (New England states: MA, CT, RI, VT, NH, ME) with HTTP ETag, Last-Modified, HTTP range resume, and SHA256 checksum verification.
- Seamless PBF dataset merging using host `osmium` binary with automatic Docker fallback (`stefda/osmium-tool`).
- Docker container integration for OpenStreetMap Carto tile server (`overv/openstreetmap-tile-server`).
- Support for multi-threaded layered tile generation and bounding box presets (`western-mass-max`, `western-massachusetts`, `massachusetts`, `new-england`, `southern-vermont`, `southern-new-hampshire`).
- Resumable tile generation with exact skip detection for existing valid PNG tiles.
- Lossless PNG optimization via `oxipng` (with Pillow fallback).
- Rich terminal UI with live system resource display (CPU %, Disk usage, Remaining SD storage).
- CLI commands: `init`, `build`, `update`, `estimate`, `clean`.
- Complete test suite, type hints (`mypy`), linting (`ruff`), and GitHub Actions CI workflow.
