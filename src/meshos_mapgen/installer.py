"""System dependency checker and auto-installer helper for osmium-tool and oxipng."""

import logging
import shutil
import subprocess
import sys

from rich.console import Console
from rich.prompt import Confirm

logger = logging.getLogger(__name__)
console = Console()


def detect_package_manager() -> tuple[str, list[str]] | None:
    """Detect local system package manager and return install command prefix."""
    if sys.platform.startswith("linux"):
        if shutil.which("apt-get"):
            return (
                "apt-get",
                ["sudo", "apt-get", "update", "&&", "sudo", "apt-get", "install", "-y"],
            )
        elif shutil.which("pacman"):
            return ("pacman", ["sudo", "pacman", "-S", "--noconfirm"])
        elif shutil.which("dnf"):
            return ("dnf", ["sudo", "dnf", "install", "-y"])
    elif sys.platform == "darwin":
        if shutil.which("brew"):
            return ("brew", ["brew", "install"])
    return None


def get_package_name(tool_name: str, pkg_manager: str) -> str:
    """Map tool binary name to package manager package name."""
    if tool_name == "osmium":
        if pkg_manager in ("apt-get", "pacman", "dnf", "brew"):
            return "osmium-tool"
    elif tool_name == "oxipng":
        return "oxipng"
    return tool_name


def ensure_system_tool(
    tool_name: str,
    purpose: str,
    interactive: bool = True,
) -> bool:
    """Check if tool exists. Prompt to auto-install if missing, or return False for fallback."""
    if shutil.which(tool_name):
        return True

    logger.info(f"System tool '{tool_name}' ({purpose}) is missing locally.")

    pkg_info = detect_package_manager()
    if not pkg_info:
        logger.info(f"No supported package manager detected. Will fall back for '{tool_name}'.")
        return False

    pkg_manager, cmd_prefix = pkg_info
    pkg_name = get_package_name(tool_name, pkg_manager)

    if interactive and sys.stdin.isatty():
        should_install = Confirm.ask(
            f"[bold yellow]Tool '{tool_name}' is missing.[/bold yellow] "
            f"Auto-install [cyan]{pkg_name}[/cyan] via [bold]{pkg_manager}[/bold]?",
            default=True,
        )
        if should_install:
            console.print(f"[bold cyan]Installing {pkg_name} via {pkg_manager}...[/bold cyan]")
            try:
                if pkg_manager == "apt-get":
                    full_cmd = ["sudo", "apt-get", "install", "-y", pkg_name]
                else:
                    full_cmd = [*cmd_prefix, pkg_name]
                res = subprocess.run(full_cmd)

                if res.returncode == 0 and shutil.which(tool_name):
                    console.print(f"[bold green]Successfully installed {tool_name}![/bold green]")
                    return True
            except Exception as e:
                console.print(f"[bold red]Auto-install failed:[/bold red] {e}")

    logger.info(f"Using portable fallback for '{tool_name}'.")
    return False
