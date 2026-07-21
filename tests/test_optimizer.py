"""Unit tests for PNG optimizer."""

from pathlib import Path

from PIL import Image

from meshos_mapgen.optimizer import PNGOptimizer


def test_png_optimizer_single_pass(tmp_path: Path) -> None:
    tiles_dir = tmp_path / "tiles" / "10" / "200"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    img_path = tiles_dir / "300.png"
    img = Image.new("RGB", (256, 256), color="red")
    img.save(img_path, "PNG")

    optimizer = PNGOptimizer(num_threads=2)
    opt_count, skip_count = optimizer.optimize_tiles(tmp_path / "tiles")

    assert opt_count == 1
    assert skip_count == 0

    # Second run should skip already optimized tile
    opt_count2, skip_count2 = optimizer.optimize_tiles(tmp_path / "tiles")
    assert opt_count2 == 0
    assert skip_count2 == 1
