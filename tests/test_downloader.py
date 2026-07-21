"""Unit tests for Geofabrik downloader."""

from pathlib import Path

import pytest

from meshos_mapgen.downloader import GeofabrikDownloader


def test_get_state_url() -> None:
    downloader = GeofabrikDownloader()
    url = downloader.get_state_url("massachusetts")
    assert url == "https://download.geofabrik.de/north-america/us/massachusetts-latest.osm.pbf"

    url2 = downloader.get_state_url("new_hampshire")
    assert url2 == "https://download.geofabrik.de/north-america/us/new-hampshire-latest.osm.pbf"

    with pytest.raises(ValueError):
        downloader.get_state_url("invalid_state_123")


@pytest.mark.asyncio
async def test_checksum_verification(tmp_path: Path) -> None:
    downloader = GeofabrikDownloader(cache_dir=tmp_path)
    test_file = tmp_path / "sample.txt"
    test_file.write_text("meshos-mapgen test content\n", encoding="utf-8")

    # MD5 of "meshos-mapgen test content\n" is 6b91122a275f92ff48e24c3e80d4bd5e
    import hashlib
    computed_md5 = hashlib.md5(test_file.read_bytes()).hexdigest()

    assert await downloader.verify_checksum(test_file, computed_md5)
    assert not await downloader.verify_checksum(test_file, "00000000000000000000000000000000")
