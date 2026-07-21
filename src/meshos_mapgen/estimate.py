"""Estimation engine for computing tile counts, disk storage, and render times."""

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from meshos_mapgen.config import MapGenConfig
from meshos_mapgen.tiles import generate_region_tiles

AVG_TILE_SIZE_BYTES = 20 * 1024  # ~20 KB per PNG tile
AVG_RENDER_TILES_PER_SEC = 25.0   # ~25 tiles/sec on multi-thread system


@dataclass
class RegionEstimate:
    """Estimated metrics for a single region."""

    name: str
    zoom_str: str
    total_tiles: int
    existing_tiles: int
    missing_tiles: int
    est_bytes: int
    est_render_seconds: float


@dataclass
class TotalEstimate:
    """Overall estimation summary."""

    regions: list[RegionEstimate]
    total_tiles: int
    existing_tiles: int
    missing_tiles: int
    total_bytes: int
    total_render_seconds: float

    def format_bytes(self) -> str:
        """Format total estimated bytes into human readable string."""
        gb = self.total_bytes / (1024**3)
        if gb >= 1.0:
            return f"{gb:.2f} GB"
        mb = self.total_bytes / (1024**2)
        return f"{mb:.1f} MB"

    def format_time(self) -> str:
        """Format total estimated render time into human readable string."""
        mins, secs = divmod(int(self.total_render_seconds), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours}h {mins}m {secs}s"
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"


def estimate_config(config: MapGenConfig) -> TotalEstimate:
    """Calculate estimation metrics for all regions in configuration."""
    tiles_dir = config.resolve_tiles_dir()
    threads = config.resolve_threads()
    tiles_per_sec = AVG_RENDER_TILES_PER_SEC * (threads / 4.0)

    region_estimates: list[RegionEstimate] = []
    grand_total = 0
    grand_existing = 0
    grand_missing = 0

    for region in config.regions:
        total = 0
        existing = 0

        for tile in generate_region_tiles(region):
            total += 1
            tile_path = tiles_dir / str(tile.z) / str(tile.x) / f"{tile.y}.png"
            if tile_path.is_file() and tile_path.stat().st_size > 0:
                existing += 1

        missing = total - existing
        est_bytes = total * AVG_TILE_SIZE_BYTES
        est_render_sec = missing / tiles_per_sec if tiles_per_sec > 0 else 0.0

        region_estimates.append(
            RegionEstimate(
                name=region.name,
                zoom_str=str(region.zoom),
                total_tiles=total,
                existing_tiles=existing,
                missing_tiles=missing,
                est_bytes=est_bytes,
                est_render_seconds=est_render_sec,
            )
        )

        grand_total += total
        grand_existing += existing
        grand_missing += missing

    grand_bytes = grand_total * AVG_TILE_SIZE_BYTES
    grand_sec = grand_missing / tiles_per_sec if tiles_per_sec > 0 else 0.0

    return TotalEstimate(
        regions=region_estimates,
        total_tiles=grand_total,
        existing_tiles=grand_existing,
        missing_tiles=grand_missing,
        total_bytes=grand_bytes,
        total_render_seconds=grand_sec,
    )


def print_estimate_report(config: MapGenConfig, console: Console | None = None) -> None:
    """Print formatted estimation report table to Rich console."""
    if console is None:
        console = Console()

    est = estimate_config(config)

    table = Table(
        title="[bold cyan]MeshOS Tile Generation Estimate[/bold cyan]",
        border_style="cyan",
    )
    table.add_column("Region Name", style="bold white")
    table.add_column("Zoom Range", style="yellow")
    table.add_column("Total Tiles", justify="right", style="cyan")
    table.add_column("Existing", justify="right", style="green")
    table.add_column("Missing", justify="right", style="magenta")
    table.add_column("Est. Storage", justify="right", style="blue")
    table.add_column("Est. Render Time", justify="right", style="dim white")

    for reg in est.regions:
        mb = reg.est_bytes / (1024**2)
        mins, secs = divmod(int(reg.est_render_seconds), 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        table.add_row(
            reg.name,
            reg.zoom_str,
            f"{reg.total_tiles:,}",
            f"{reg.existing_tiles:,}",
            f"{reg.missing_tiles:,}",
            f"{mb:.1f} MB",
            time_str,
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "-",
        f"[bold]{est.total_tiles:,}[/bold]",
        f"[bold]{est.existing_tiles:,}[/bold]",
        f"[bold]{est.missing_tiles:,}[/bold]",
        f"[bold]{est.format_bytes()}[/bold]",
        f"[bold]{est.format_time()}[/bold]",
    )

    console.print()
    console.print(table)
    console.print(
        Panel(
            f"[bold green]Target SD Card Directory:[/bold green] {config.resolve_tiles_dir()}\n"
            f"[bold green]Allocated Threads:[/bold green] {config.resolve_threads()} threads\n"
            f"[bold green]PNG Optimization Enabled:[/bold green] {config.optimize_png}",
            title="Configuration Summary",
            border_style="green",
        )
    )
