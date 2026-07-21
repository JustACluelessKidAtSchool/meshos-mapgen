"""PNG Optimizer module utilizing oxipng for lossless compression."""

import json
import logging
import shutil
import subprocess
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def _optimize_single_file_oxipng(file_path_str: str) -> bool:
    """Helper worker to run oxipng CLI on a single file."""
    try:
        cmd = ["oxipng", "-o", "2", "--strip", "safe", file_path_str]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def _optimize_single_file_pil(file_path_str: str) -> bool:
    """Fallback lossless optimization using Pillow."""
    try:
        path = Path(file_path_str)
        with Image.open(path) as img:
            img.save(path, "PNG", optimize=True)
        return True
    except Exception:
        return False


class PNGOptimizer:
    """Optimizes rendered PNG tile files losslessly."""

    def __init__(self, num_threads: int = 4) -> None:
        self.num_threads = max(1, num_threads)
        from meshos_mapgen.installer import ensure_system_tool
        has_oxipng = ensure_system_tool("oxipng", "lossless PNG optimization")
        self.oxipng_bin = shutil.which("oxipng") if has_oxipng else None

    def optimize_tiles(
        self,
        tiles_dir: Path,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Optimize all PNG files in tiles_dir. Returns (optimized_count, skipped_count)."""
        tiles_dir = Path(tiles_dir).expanduser().resolve()
        if not tiles_dir.is_dir():
            return (0, 0)

        manifest_path = tiles_dir / ".optimized_manifest.json"
        manifest: dict[str, float] = {}
        if manifest_path.is_file():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}

        png_files = list(tiles_dir.glob("*/*/*.png"))
        total_files = len(png_files)

        files_to_optimize: list[Path] = []
        skipped_count = 0

        for png in png_files:
            rel = str(png.relative_to(tiles_dir))
            mtime = png.stat().st_mtime
            if rel in manifest and manifest[rel] >= mtime:
                skipped_count += 1
            else:
                files_to_optimize.append(png)

        if not files_to_optimize:
            if progress_callback:
                progress_callback(total_files, 0, skipped_count)
            return (0, skipped_count)

        use_oxipng = self.oxipng_bin is not None
        worker_fn = _optimize_single_file_oxipng if use_oxipng else _optimize_single_file_pil

        if use_oxipng:
            logger.info(f"Optimizing {len(files_to_optimize)} tiles using oxipng...")
        else:
            logger.info(
                f"oxipng binary not found. Falling back to Pillow lossless optimization "
                f"for {len(files_to_optimize)} tiles..."
            )

        optimized_count = 0
        processed_count = skipped_count

        with ProcessPoolExecutor(max_workers=self.num_threads) as executor:
            future_to_file = {
                executor.submit(worker_fn, str(p)): p for p in files_to_optimize
            }
            for future in as_completed(future_to_file):
                p = future_to_file[future]
                processed_count += 1
                try:
                    success = future.result()
                    if success:
                        optimized_count += 1
                        rel = str(p.relative_to(tiles_dir))
                        manifest[rel] = p.stat().st_mtime
                except Exception as ex:
                    logger.warning(f"Optimization failed for {p.name}: {ex}")

                if progress_callback:
                    progress_callback(processed_count, optimized_count, skipped_count)

        # Save manifest
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)
        except Exception as e:
            logger.warning(f"Failed to write optimization manifest: {e}")

        return (optimized_count, skipped_count)
