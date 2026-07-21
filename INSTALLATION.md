# Installation Guide for meshos-mapgen

`meshos-mapgen` is a cross-platform CLI tool supporting **Linux**, **macOS**, and **Windows (via WSL2 or Docker Desktop)**.

---

## Supported Operating Systems

- **Linux**: Ubuntu 24.04+, Linux Mint 22+, Debian 13+, Arch, Fedora
- **macOS**: macOS 12+ (Intel & Apple Silicon with Docker Desktop or Colima)
- **Windows**: Windows 10 / 11 (via WSL2 or Docker Desktop for Windows)

---

## Prerequisites

### 1. Python 3.12+ and pip / pipx

Ensure Python 3.12 or higher is installed:

```bash
python3 --version
```

Install `pipx` for isolated CLI tool installation:

- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y python3-pip python3-pipx && pipx ensurepath
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install pipx && pipx ensurepath
  ```
- **Windows / Portable**:
  ```bash
  python -m pip install --user pipx && pipx ensurepath
  ```

### 2. Docker Engine / Docker Desktop

`meshos-mapgen` relies on Docker to run OpenStreetMap Carto rendering containers and Osmium data merging utilities.

- **Linux**: Install `docker.io` and add your user to the `docker` group:
  ```bash
  sudo apt install -y docker.io
  sudo usermod -aG docker $USER
  newgrp docker
  ```
- **macOS / Windows**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and ensure Docker service is running.

---

## Automatic Package Installer & Fallbacks

When running `meshos-mapgen build`, the tool automatically checks for missing native system binaries (`osmium-tool` and `oxipng`).

- **Auto-Installer Prompt**: If missing, `meshos-mapgen` will offer to automatically install them using your system package manager (`apt`, `brew`, `pacman`, `dnf`) using `sudo` or user privilege escalation.
- **Portable Fallback**: If auto-install is declined or unavailable, `meshos-mapgen` seamlessly falls back to Docker containers (`stefda/osmium-tool`) and Python Pillow lossless optimization without requiring any manual action.

---

## Installing `meshos-mapgen`

### Option A: Via pipx (Recommended)

```bash
pipx install meshos-mapgen
```

To update in the future:

```bash
pipx upgrade meshos-mapgen
```

### Option B: Installing from Source

```bash
git clone https://github.com/JustACluelessKidAtSchool/meshos-mapgen.git
cd meshos-mapgen
pip install -e .[dev]
```

Verify installation:

```bash
meshos-mapgen --version
```
