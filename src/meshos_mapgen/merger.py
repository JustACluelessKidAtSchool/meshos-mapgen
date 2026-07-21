"""Merger for combining multiple OSM PBF files using local osmium CLI or Docker container."""

import logging
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import docker

logger = logging.getLogger(__name__)


class MergeError(Exception):
    """Exception raised when merging PBF files fails."""

    pass


class PBFMerger:
    """Combines multiple OpenStreetMap PBF files into a unified dataset."""

    def __init__(self, docker_image: str = "stefda/osmium-tool:latest") -> None:
        self.docker_image = docker_image

    def merge(self, pbf_files: Sequence[Path], output_path: Path, force: bool = False) -> Path:
        """Merge multiple PBF files into output_path using local osmium or Docker."""
        if not pbf_files:
            raise ValueError("No PBF files provided for merging.")

        output_path = Path(output_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(pbf_files) == 1:
            single_file = Path(pbf_files[0]).resolve()
            if single_file != output_path:
                logger.info(
                    f"Only 1 PBF file provided. Copying {single_file.name} to {output_path.name}"
                )
                shutil.copy2(single_file, output_path)
            return output_path

        if output_path.is_file() and not force:
            logger.info(f"Merged PBF file {output_path.name} already exists. Skipping merge.")
            return output_path

        from meshos_mapgen.installer import ensure_system_tool

        has_local_osmium = ensure_system_tool("osmium", "fast OSM dataset merging")
        if has_local_osmium:
            logger.info("Local 'osmium' binary detected. Merging PBF files using host osmium...")
            self._merge_local(pbf_files, output_path)
        else:
            logger.info(
                "Local 'osmium' binary missing/declined. Falling back to Docker osmium container..."
            )
            self._merge_docker(pbf_files, output_path)

        return output_path

    def _merge_local(self, pbf_files: Sequence[Path], output_path: Path) -> None:
        """Merge using local osmium binary."""
        cmd = [
            "osmium",
            "merge",
            *[str(p.resolve()) for p in pbf_files],
            "-o",
            str(output_path),
            "--overwrite",
        ]
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise MergeError(f"osmium merge failed: {result.stderr}")

    def _merge_docker(self, pbf_files: Sequence[Path], output_path: Path) -> None:
        """Merge using stefda/osmium-tool Docker container."""
        try:
            client = docker.from_env()
        except Exception as e:
            raise MergeError(
                f"Failed to connect to Docker daemon: {e}. Please ensure Docker is running."
            ) from e

        try:
            client.images.get(self.docker_image)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image {self.docker_image}...")
            client.images.pull(self.docker_image)

        # Collect unique parent directories to mount into container
        parent_dirs = {p.resolve().parent for p in pbf_files}
        parent_dirs.add(output_path.parent)

        volumes: dict[str, dict[str, str]] = {}
        dir_map: dict[Path, str] = {}
        for idx, d in enumerate(parent_dirs):
            container_dir = f"/data_{idx}"
            volumes[str(d)] = {"bind": container_dir, "mode": "rw"}
            dir_map[d] = container_dir

        container_inputs = [
            f"{dir_map[p.resolve().parent]}/{p.name}" for p in pbf_files
        ]
        container_output = f"{dir_map[output_path.parent]}/{output_path.name}"

        command = [
            "osmium",
            "merge",
            *container_inputs,
            "-o",
            container_output,
            "--overwrite",
        ]

        logger.info("Executing osmium merge in Docker container...")
        try:
            client.containers.run(
                self.docker_image,
                command=command,
                volumes=volumes,
                remove=True,
                detach=False,
            )
        except docker.errors.ContainerError as ce:
            raise MergeError(f"Docker container merge failed: {ce.stderr}") from ce
        except Exception as ex:
            raise MergeError(f"Failed to run osmium container: {ex}") from ex
