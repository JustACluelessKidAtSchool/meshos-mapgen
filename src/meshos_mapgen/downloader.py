"""Downloader for Geofabrik OSM PBF extracts with ETag, resume, and checksum support."""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiohttp

from meshos_mapgen.presets import DEFAULT_GEOFABRIK_BASE_URL, GEOFABRIK_STATES

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when file download fails."""

    pass


class GeofabrikDownloader:
    """Async downloader for Geofabrik OSM PBF data files."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "meshos-mapgen" / "pbfs"
        else:
            self.cache_dir = Path(cache_dir).expanduser().resolve()

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_state_url(self, state_key: str) -> str:
        """Get Geofabrik download URL for a state."""
        normalized = state_key.lower().replace("_", "-")
        if normalized not in GEOFABRIK_STATES:
            valid_states = list(set(GEOFABRIK_STATES.keys()))
            raise ValueError(
                f"Unsupported state '{state_key}'. Supported states: {valid_states}"
            )
        filename = f"{GEOFABRIK_STATES[normalized]}-latest.osm.pbf"
        return f"{DEFAULT_GEOFABRIK_BASE_URL}/{filename}"

    async def download_file(
        self,
        url: str,
        dest_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
        force: bool = False,
    ) -> Path:
        """Download a file with ETag, Last-Modified, HTTP range resume, and metadata tracking."""
        meta_path = dest_path.with_suffix(dest_path.suffix + ".meta.json")
        meta_data: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta_data = json.load(f)
            except Exception:
                meta_data = {}

        headers: dict[str, str] = {}
        file_exists = dest_path.is_file()
        existing_size = dest_path.stat().st_size if file_exists else 0

        async with aiohttp.ClientSession() as session:
            # First perform HEAD request to check remote size and headers
            try:
                async with session.head(url, allow_redirects=True) as head_resp:
                    if head_resp.status == 200:
                        remote_etag = head_resp.headers.get("ETag", "")
                        remote_lm = head_resp.headers.get("Last-Modified", "")
                        remote_size = int(head_resp.headers.get("Content-Length", 0))

                        # If not forcing, check if fully downloaded and unchanged
                        if (
                            not force
                            and file_exists
                            and existing_size == remote_size
                            and remote_size > 0
                        ):
                            if (
                                remote_etag and meta_data.get("etag") == remote_etag
                            ) or (
                                remote_lm and meta_data.get("last_modified") == remote_lm
                            ):
                                logger.info(
                                    f"File {dest_path.name} is up to date. Skipping download."
                                )
                                return dest_path
            except Exception as e:
                logger.warning(f"HEAD request failed for {url}: {e}")
                remote_etag = ""
                remote_lm = ""
                remote_size = 0

            # Set up range headers if resuming
            if file_exists and existing_size > 0 and not force:
                headers["Range"] = f"bytes={existing_size}-"

            mode = "ab" if ("Range" in headers and file_exists) else "wb"
            if mode == "wb":
                existing_size = 0

            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status not in (200, 206):
                    raise DownloadError(
                        f"Failed to download {url}: HTTP {resp.status}"
                    )

                content_length = int(resp.headers.get("Content-Length", 0))
                total_size = existing_size + content_length
                downloaded = existing_size

                remote_etag = resp.headers.get("ETag", remote_etag)
                remote_lm = resp.headers.get("Last-Modified", remote_lm)

                with open(dest_path, mode) as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            # Save metadata
            new_meta = {
                "url": url,
                "etag": remote_etag,
                "last_modified": remote_lm,
                "size": total_size,
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(new_meta, f, indent=2)

        return dest_path

    async def download_checksum(self, url: str) -> str | None:
        """Download MD5 or SHA256 file if available."""
        async with aiohttp.ClientSession() as session:
            for ext in (".md5", ".sha256"):
                try:
                    async with session.get(url + ext) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            # Extracts hash token (first word)
                            return text.strip().split()[0]
                except Exception:
                    continue
        return None

    async def verify_checksum(self, file_path: Path, expected_hash: str) -> bool:
        """Verify MD5 or SHA256 checksum of a downloaded file."""
        is_md5 = len(expected_hash) == 32
        hasher = hashlib.md5() if is_md5 else hashlib.sha256()

        def _compute() -> str:
            with open(file_path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    hasher.update(chunk)
            return hasher.hexdigest()

        computed = await asyncio.to_thread(_compute)
        return computed.lower() == expected_hash.lower()

    async def download_state_pbf(
        self,
        state_key: str,
        progress_callback: Callable[[int, int], None] | None = None,
        force: bool = False,
    ) -> Path:
        """Download PBF for a single state into cache directory."""
        url = self.get_state_url(state_key)
        filename = url.split("/")[-1]
        dest_path = self.cache_dir / filename

        path = await self.download_file(
            url=url,
            dest_path=dest_path,
            progress_callback=progress_callback,
            force=force,
        )

        checksum = await self.download_checksum(url)
        if checksum:
            valid = await self.verify_checksum(path, checksum)
            if not valid:
                logger.warning(
                    f"Checksum verification failed for {path.name}. Re-downloading..."
                )
                path = await self.download_file(
                    url=url,
                    dest_path=dest_path,
                    progress_callback=progress_callback,
                    force=True,
                )

        return path
