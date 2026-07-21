"""Typer CLI interface for meshos-mapgen."""

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import TaskID

from meshos_mapgen import __version__
from meshos_mapgen.config import MapGenConfig
from meshos_mapgen.downloader import GeofabrikDownloader
from meshos_mapgen.estimate import print_estimate_report
from meshos_mapgen.merger import PBFMerger
from meshos_mapgen.optimizer import PNGOptimizer
from meshos_mapgen.renderer import TileRenderer
from meshos_mapgen.ui import create_progress_bar, create_system_stats_panel, print_banner

app = typer.Typer(
    name="meshos-mapgen",
    help="Generate offline OpenStreetMap raster tiles for MeshOS running on LilyGO T-Deck.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold green]meshos-mapgen[/bold green] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug logging output."),
    ] = False,
) -> None:
    """MeshOS Map Generator CLI."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")


@app.command()
def init(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Target output configuration YAML file path.",
        ),
    ] = Path("config.yaml"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing configuration file."),
    ] = False,
) -> None:
    """Create a default YAML configuration file (western-mass-max profile)."""
    print_banner()
    output_path = output.resolve()
    if output_path.is_file() and not force:
        console.print(
            f"[bold red]Error:[/bold red] Configuration file "
            f"[cyan]{output_path}[/cyan] already exists. "
            "Use [bold]--force[/bold] to overwrite."
        )
        raise typer.Exit(code=1)

    content = MapGenConfig.get_default_yaml_content()
    output_path.write_text(content, encoding="utf-8")
    console.print(
        f"[bold green]Created default configuration file:[/bold green] [cyan]{output_path}[/cyan]\n"
        "Profile: [bold yellow]western-mass-max[/bold yellow]\n"
        "To start tile generation, run: [bold]meshos-mapgen build config.yaml[/bold]"
    )


@app.command()
def estimate(
    config_file: Annotated[
        Path,
        typer.Argument(
            help="Path to YAML configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = Path("config.yaml"),
) -> None:
    """Estimate total tiles, storage requirements, and render time."""
    print_banner()
    config = MapGenConfig.from_yaml_file(config_file)
    print_estimate_report(config, console)


@app.command()
def build(
    config_file: Annotated[
        Path,
        typer.Argument(
            help="Path to YAML configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = Path("config.yaml"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force re-download and re-rendering of all tiles."),
    ] = False,
) -> None:
    """Perform a complete tile build pipeline."""
    print_banner()
    config = MapGenConfig.from_yaml_file(config_file)
    console.print(create_system_stats_panel(config.resolve_output_dir()))

    # Step 1: Resolve states to download
    states_to_download = {
        "massachusetts",
        "connecticut",
        "rhode-island",
        "vermont",
        "new-hampshire",
        "maine",
    }
    console.print("\n[bold cyan]Step 1/5: Downloading Geofabrik OSM Extracts...[/bold cyan]")
    downloader = GeofabrikDownloader()
    downloaded_pbfs: list[Path] = []

    progress = create_progress_bar()
    with progress:
        for state in sorted(states_to_download):
            task_id = progress.add_task(f"Downloading {state}", total=100)

            def update_cb(dl: int, tot: int, tid: TaskID = task_id) -> None:
                if tot > 0:
                    progress.update(tid, completed=dl, total=tot)

            try:
                pbf_path = asyncio.run(
                    downloader.download_state_pbf(state, progress_callback=update_cb, force=force)
                )
                downloaded_pbfs.append(pbf_path)
            except Exception as ex:
                console.print(f"[bold red]Failed to download {state}:[/bold red] {ex}")
                raise typer.Exit(code=1)

    # Step 2: Merge PBFs
    console.print("\n[bold cyan]Step 2/5: Merging PBF Datasets...[/bold cyan]")
    merged_output = downloader.cache_dir / "merged_new_england.osm.pbf"
    merger = PBFMerger()
    try:
        merged_pbf = merger.merge(downloaded_pbfs, merged_output, force=force)
        console.print(f"[bold green]Merged PBF dataset ready:[/bold green] {merged_pbf}")
    except Exception as ex:
        console.print(f"[bold red]PBF merge failed:[/bold red] {ex}")
        raise typer.Exit(code=1)

    # Step 3 & 4: Import & Render Tiles
    console.print("\n[bold cyan]Step 3/5: Initializing Docker Tile Server...[/bold cyan]")
    renderer = TileRenderer(config)
    try:
        renderer.prepare_renderer(merged_pbf, force_reimport=force)
        renderer.start_server()
    except Exception as ex:
        console.print(f"[bold red]Tile server initialization failed:[/bold red] {ex}")
        raise typer.Exit(code=1)

    console.print("\n[bold cyan]Step 4/5: Rendering OpenStreetMap Raster Tiles...[/bold cyan]")
    try:
        for region in config.regions:
            console.print(
                f"\n[bold yellow]Rendering Region: {region.name} "
                f"(Zoom {region.zoom})[/bold yellow]"
            )
            progress = create_progress_bar()
            with progress:
                task_id = progress.add_task(f"Rendering {region.name}", total=100)

                def render_cb(proc: int, rend: int, skip: int, tid: TaskID = task_id) -> None:
                    # Proc is percentage
                    progress.update(tid, completed=proc)

                rendered, skipped = asyncio.run(
                    renderer.render_region_tiles_async(region, progress_callback=render_cb)
                )
                console.print(
                    f"Region {region.name} complete: "
                    f"[green]{rendered} rendered[/green], [cyan]{skipped} skipped[/cyan]."
                )
    finally:
        renderer.stop_server()

    # Step 5: Optimize PNGs
    if config.optimize_png:
        console.print("\n[bold cyan]Step 5/5: Lossless PNG Optimization (oxipng)...[/bold cyan]")
        optimizer = PNGOptimizer(num_threads=config.resolve_threads())
        opt_count, opt_skipped = optimizer.optimize_tiles(config.resolve_tiles_dir())
        console.print(
            f"PNG optimization complete: "
            f"[green]{opt_count} optimized[/green], [cyan]{opt_skipped} skipped[/cyan]."
        )

    tiles_dir = config.resolve_tiles_dir()
    console.print(
        f"\n[bold green]SUCCESS![/bold green] MeshOS map tiles generated successfully at:\n"
        f"[bold cyan]{tiles_dir}[/bold cyan]\n\n"
        "Copy the [bold]tiles/[/bold] folder directly to the root of your "
        "LilyGO T-Deck micro SD card!"
    )


@app.command()
def update(
    config_file: Annotated[
        Path,
        typer.Argument(
            help="Path to YAML configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = Path("config.yaml"),
) -> None:
    """Check for updated Geofabrik extracts and incrementally update changed tiles."""
    print_banner()
    console.print("[bold yellow]Checking for updated Geofabrik extracts...[/bold yellow]")
    # Run build without force (built-in ETag / Last-Modified checks handle updates automatically)
    build(config_file=config_file, force=False)


@app.command()
def clean() -> None:
    """Stop Docker tile server container and remove PostgreSQL cache volume."""
    print_banner()
    console.print(
        "[bold yellow]Cleaning Docker containers and tile server cache volume...[/bold yellow]"
    )
    config = MapGenConfig()
    renderer = TileRenderer(config)
    renderer.clean_cache()
    console.print("[bold green]Cleanup complete![/bold green]")


if __name__ == "__main__":
    app()
