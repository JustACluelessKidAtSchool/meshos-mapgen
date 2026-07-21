"""Unit tests for system tool auto-installer helper."""

import shutil

from meshos_mapgen.installer import detect_package_manager, ensure_system_tool, get_package_name


def test_detect_package_manager() -> None:
    pkg_info = detect_package_manager()
    if shutil.which("apt-get"):
        assert pkg_info is not None
        assert pkg_info[0] == "apt-get"


def test_get_package_name() -> None:
    assert get_package_name("osmium", "apt-get") == "osmium-tool"
    assert get_package_name("oxipng", "apt-get") == "oxipng"


def test_ensure_system_tool_non_interactive() -> None:
    # Non-interactive check for python3 should return True since python3 exists
    assert ensure_system_tool("python3", "testing python", interactive=False)
