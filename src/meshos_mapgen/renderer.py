"""Docker-based OpenStreetMap Carto renderer and multi-threaded tile generator."""

import asyncio
import logging
import time
from collections.abc import Callable
from pathlib import Path

import aiohttp
import docker
from PIL import Image

from meshos_mapgen.config import MapGenConfig, RegionConfig
from meshos_mapgen.tiles import TileCoord, generate_region_tiles

logger = logging.getLogger(__name__)


class RenderError(Exception):
    """Exception raised when tile rendering fails."""

    pass


class TileRenderer:
    """Manages Docker OpenStreetMap tile server and renders XYZ PNG tiles."""

    def __init__(
        self,
        config: MapGenConfig,
        docker_image: str = "overv/openstreetmap-tile-server:latest",
        container_port: int = 8080,
    ) -> None:
        self.config = config
        self.docker_image = docker_image
        self.container_port = container_port
        self.container_name = "meshos-tile-server"
        self.volume_name = "meshos-tile-pgdata"
        self.output_dir = config.resolve_output_dir()
        self.tiles_dir = config.resolve_tiles_dir()
        self.tiles_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path.home() / ".cache" / "meshos-mapgen"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_docker_client(self) -> docker.DockerClient:
        try:
            return docker.from_env()
        except Exception as e:
            raise RenderError(
                f"Failed to connect to Docker daemon: {e}. Ensure Docker is running."
            ) from e

    def prepare_renderer(self, merged_pbf: Path, force_reimport: bool = False) -> None:
        """Ensure Docker image is pulled and PBF data is imported into PostgreSQL cache volume."""
        client = self._get_docker_client()

        # Pull image if missing
        try:
            client.images.get(self.docker_image)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling renderer image {self.docker_image}...")
            client.images.pull(self.docker_image)

        # Create pgdata volume if missing
        try:
            client.volumes.get(self.volume_name)
        except docker.errors.NotFound:
            logger.info(f"Creating Docker volume '{self.volume_name}' for PostgreSQL tile cache...")
            client.volumes.create(name=self.volume_name)

        import_marker = self.cache_dir / f".imported_{merged_pbf.name}.marker"

        if import_marker.is_file() and not force_reimport:
            logger.info("Existing imported database cache detected. Reusing cache.")
            return

        logger.info(
            "Importing PBF dataset into OpenStreetMap Carto renderer database. "
            "This may take a few minutes..."
        )

        pbf_abs = merged_pbf.resolve()
        volumes_config = {
            str(pbf_abs): {"bind": "/data/region.osm.pbf", "mode": "ro"},
            self.volume_name: {"bind": "/var/lib/postgresql/15/main", "mode": "rw"},
        }

        try:
            # Run import container
            client.containers.run(
                self.docker_image,
                command="import",
                volumes=volumes_config,
                remove=True,
                detach=False,
            )
            logger.info("PBF import complete!")
            import_marker.write_text(f"Imported {merged_pbf} at {time.time()}")
        except docker.errors.ContainerError as ce:
            raise RenderError(f"Database import container failed: {ce.stderr}") from ce
        except Exception as ex:
            raise RenderError(f"Database import failed: {ex}") from ex

    def start_server(self) -> docker.models.containers.Container:
        """Start the renderer container in daemon mode if not already running."""
        client = self._get_docker_client()

        try:
            existing = client.containers.get(self.container_name)
            if existing.status == "running":
                logger.info(f"Tile server container '{self.container_name}' is already running.")
                return existing
            else:
                logger.info(f"Starting existing container '{self.container_name}'...")
                existing.start()
                self._wait_for_server_ready()
                return existing
        except docker.errors.NotFound:
            pass

        logger.info(f"Launching tile server container '{self.container_name}'...")
        volumes_config = {
            self.volume_name: {"bind": "/var/lib/postgresql/15/main", "mode": "rw"}
        }
        port_config = {"80/tcp": self.container_port}

        try:
            container = client.containers.run(
                self.docker_image,
                command="run",
                name=self.container_name,
                volumes=volumes_config,
                ports=port_config,
                detach=True,
                remove=False,
            )
            self._wait_for_server_ready()
            return container
        except Exception as e:
            raise RenderError(f"Failed to start tile server container: {e}") from e

    def _wait_for_server_ready(self, timeout: int = 60) -> None:
        """Wait for HTTP tile endpoint to become responsive."""
        logger.info("Waiting for tile server to become ready...")
        url = f"http://localhost:{self.container_port}/tile/0/0/0.png"
        start = time.time()
        while time.time() - start < timeout:
            try:
                import urllib.request
                req = urllib.request.urlopen(url, timeout=2)
                if req.status == 200:
                    logger.info("Tile server is ready!")
                    return
            except Exception:
                time.sleep(1)

        raise RenderError(f"Tile server failed to respond within {timeout} seconds.")

    def stop_server(self) -> None:
        """Stop and remove renderer container if running."""
        client = self._get_docker_client()
        try:
            container = client.containers.get(self.container_name)
            logger.info(f"Stopping container '{self.container_name}'...")
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error stopping container: {e}")

    def clean_cache(self) -> None:
        """Remove PostgreSQL cache volume and marker files."""
        self.stop_server()
        client = self._get_docker_client()
        try:
            volume = client.volumes.get(self.volume_name)
            volume.remove(force=True)
            logger.info("Removed Docker cache volume.")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error removing Docker volume: {e}")

        for marker in self.cache_dir.glob(".imported_*.marker"):
            try:
                marker.unlink()
            except Exception:
                pass

    def is_tile_valid(self, tile_path: Path) -> bool:
        """Check if local tile file exists and is a valid PNG image."""
        if not tile_path.is_file() or tile_path.stat().st_size == 0:
            return False
        try:
            with Image.open(tile_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    async def render_tile(
        self,
        session: aiohttp.ClientSession,
        tile: TileCoord,
        semaphore: asyncio.Semaphore,
    ) -> bool:
        """Fetch a single tile from tile server and save to disk."""
        tile_path = self.tiles_dir / str(tile.z) / str(tile.x) / f"{tile.y}.png"

        if self.is_tile_valid(tile_path):
            return True  # Skipped (already rendered)

        tile_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"http://localhost:{self.container_port}/tile/{tile.z}/{tile.x}/{tile.y}.png"

        async with semaphore:
            for attempt in range(3):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            temp_path = tile_path.with_suffix(".tmp")
                            with open(temp_path, "wb") as f:
                                f.write(data)
                            temp_path.replace(tile_path)
                            return False  # Rendered new tile
                        else:
                            await asyncio.sleep(0.5)
                except Exception as ex:
                    logger.debug(f"Attempt {attempt+1} failed for tile {tile}: {ex}")
                    await asyncio.sleep(0.5)

        raise RenderError(f"Failed to render tile {tile.relative_path()}")

    async def render_region_tiles_async(
        self,
        region: RegionConfig,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> tuple[int, int]:
        """Render missing tiles for a region. Returns (rendered_count, skipped_count)."""
        threads = self.config.resolve_threads()
        semaphore = asyncio.Semaphore(threads * 2)

        tiles_list = list(generate_region_tiles(region))
        total_tiles = len(tiles_list)

        rendered_count = 0
        skipped_count = 0
        processed_count = 0

        async with aiohttp.ClientSession() as session:
            for i in range(0, total_tiles, 200):
                batch = tiles_list[i : i + 200]
                tasks = [
                    self.render_tile(session, tile, semaphore)
                    for tile in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in results:
                    processed_count += 1
                    if isinstance(res, Exception):
                        logger.error(f"Tile render error: {res}")
                    elif res is True:
                        skipped_count += 1
                    else:
                        rendered_count += 1

                if progress_callback:
                    progress_callback(processed_count, rendered_count, skipped_count)

        return (rendered_count, skipped_count)
