"""Integration tests for Typer CLI interface."""

from pathlib import Path

from typer.testing import CliRunner

from meshos_mapgen.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "meshos-mapgen version" in result.stdout


def test_cli_init_command(tmp_path: Path) -> None:
    target_yaml = tmp_path / "config.yaml"
    result = runner.invoke(app, ["init", "--output", str(target_yaml)])
    assert result.exit_code == 0
    assert target_yaml.is_file()
    assert "western-mass-max" in target_yaml.read_text(encoding="utf-8")


def test_cli_estimate_command(tmp_path: Path) -> None:
    target_yaml = tmp_path / "config.yaml"
    runner.invoke(app, ["init", "--output", str(target_yaml)])

    result = runner.invoke(app, ["estimate", str(target_yaml)])
    assert result.exit_code == 0
    assert "MeshOS Tile Generation Estimate" in result.stdout
    assert "western" in result.stdout
