# Troubleshooting Guide for meshos-mapgen

This guide provides resolutions for common issues encountered when running `meshos-mapgen`.

---

## Common Issues & Solutions

### 1. Docker Permission Denied Error

**Symptom:**
```
RenderError: Failed to connect to Docker daemon: Permission denied. Ensure Docker is running.
```

**Solution:**
Ensure your Linux user is added to the `docker` user group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```
Restart your terminal session and verify with `docker ps`.

---

### 2. Out of Disk Space During Database Import

**Symptom:**
Import container fails or PostgreSQL logs show `No space left on device`.

**Solution:**
OpenStreetMap data imports (especially multi-state extracts) require sufficient disk space for PostgreSQL indexing.
- Ensure at least 15 GB of free space is available on your root filesystem or Docker storage directory.
- Check disk space with: `df -h`
- Clean old Docker volumes and images:
  ```bash
  meshos-mapgen clean
  docker system prune -f
  ```

---

### 3. Tiles Not Displaying on LilyGO T-Deck

**Symptom:**
T-Deck shows blank or missing map tiles.

**Solution:**
1. **SD Card Format:** Ensure your micro SD card is formatted as **FAT32** or **exFAT** (depending on MeshCore firmware requirements).
2. **Directory Structure:** Ensure the `tiles/` directory is copied directly to the **root** of the SD card:
   ```
   / (SD Card Root)
   └── tiles/
       ├── 5/
       ├── 6/
       └── ...
   ```
3. **Zoom Levels:** Verify that you have rendered tiles for the zoom level currently viewed on the T-Deck.

---

### 4. Slow Rendering Performance

**Symptom:**
Tile rendering takes longer than expected.

**Solution:**
- By default, `meshos-mapgen` uses `threads = cpu_count - 2`.
- You can override `threads` in `config.yaml` to match your system capacity (e.g. `threads: 8`).
- Install native `oxipng` and `osmium-tool` via system package manager:
  ```bash
  sudo apt install -y osmium-tool oxipng
  ```

---

### 5. Resuming Interrupted Builds

**Symptom:**
Build process was canceled or crashed mid-way.

**Solution:**
Simply re-run the build command:
```bash
meshos-mapgen build config.yaml
```
`meshos-mapgen` automatically checks existing tiles and skipping already-rendered valid PNG tiles without duplicating work.
