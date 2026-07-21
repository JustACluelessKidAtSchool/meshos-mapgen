"""Rich UI progress display and system resource monitoring using psutil."""

from pathlib import Path

import psutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

console = Console()


def get_system_stats(target_path: Path | str) -> dict[str, str | float]:
    """Retrieve system CPU, memory, and disk usage for target directory."""
    path = Path(target_path).expanduser().resolve()
    # Check parent if path doesn't exist yet
    check_dir = path if path.exists() else path.parent
    while not check_dir.exists() and check_dir != check_dir.parent:
        check_dir = check_dir.parent

    cpu_percent = psutil.cpu_percent(interval=None)
    disk_usage = psutil.disk_usage(str(check_dir))

    free_gb = disk_usage.free / (1024**3)
    total_gb = disk_usage.total / (1024**3)
    used_percent = disk_usage.percent

    return {
        "cpu_percent": cpu_percent,
        "disk_free_gb": free_gb,
        "disk_total_gb": total_gb,
        "disk_used_percent": used_percent,
    }


def create_system_stats_panel(target_path: Path | str) -> Panel:
    """Create a Rich Panel displaying current system resources."""
    stats = get_system_stats(target_path)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column(style="bold white")

    table.add_row("CPU Usage:", f"{stats['cpu_percent']:.1f}%")
    table.add_row("Disk Free:", f"{stats['disk_free_gb']:.2f} GB / {stats['disk_total_gb']:.2f} GB")
    table.add_row("Disk Usage:", f"{stats['disk_used_percent']:.1f}%")

    return Panel(table, title="[bold green]System Resources[/bold green]", border_style="green")


def create_progress_bar() -> Progress:
    """Create a configured Rich Progress instance."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def print_banner() -> None:
    """Print ASCII logo / title banner."""
    console.print(
        Panel.fit(
            "[bold green]meshos-mapgen[/bold green] — "
            "[cyan]MeshOS Offline Map Generator for LilyGO T-Deck[/cyan]\n"
            "[dim]Generating standard OpenStreetMap Carto XYZ raster tiles "
            "(tiles/{z}/{x}/{y}.png)[/dim]",
            border_style="cyan",
        )
    )
