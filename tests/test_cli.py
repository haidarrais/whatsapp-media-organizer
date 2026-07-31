"""Tests for whatsapp_media_organizer.cli."""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

from whatsapp_media_organizer.cli import build_parser

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


def _run_cli(*args):
    env = {**os.environ, "PYTHONPATH": str(SRC_ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "whatsapp_media_organizer", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--source", "/some/dir"])
    assert str(args.dest).endswith("sorted_media")
    assert args.no_rename is False
    assert args.dry_run is False


def test_cli_e2e_moves_file(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "IMG-20231026-WA0001.jpg").write_text("x")
    dest = tmp_path / "dest"

    proc = _run_cli("--source", str(src), "--dest", str(dest))

    assert proc.returncode == 0
    assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").is_file()
    assert "Moved: IMG-20231026-WA0001.jpg" in proc.stdout


def test_cli_extracts_and_sorts_zip(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    archive = src / "media.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("IMG-20231026-WA0001.jpg", "x")
    dest = tmp_path / "dest"

    proc = _run_cli("--source", str(src), "--dest", str(dest))

    assert proc.returncode == 0
    assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").is_file()
    assert not archive.exists()
    assert "Deleted archive: media.zip" in proc.stdout


def test_cli_no_extract_leaves_zip_untouched(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    archive = src / "media.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("IMG-20231026-WA0001.jpg", "x")
    dest = tmp_path / "dest"

    proc = _run_cli("--source", str(src), "--dest", str(dest), "--no-extract")

    assert proc.returncode == 0
    assert archive.exists()
    assert not (dest / "2023" / "10" / "26").exists()


def test_cli_dry_run_reports_zip_contents(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    archive = src / "media.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("IMG-20231026-WA0001.jpg", "x")
    dest = tmp_path / "dest"

    proc = _run_cli("--source", str(src), "--dest", str(dest), "--dry-run")

    assert proc.returncode == 0
    assert archive.exists()
    assert "would move : media.zip :: IMG-20231026-WA0001.jpg -> 2023/10/26/" in proc.stdout


def test_cli_dry_run_leaves_files_in_place(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "IMG-20231026-WA0001.jpg").write_text("x")
    dest = tmp_path / "dest"

    proc = _run_cli("--source", str(src), "--dest", str(dest), "--dry-run")

    assert proc.returncode == 0
    assert (src / "IMG-20231026-WA0001.jpg").exists()
    assert "would move" in proc.stdout


def test_cli_errors_when_source_missing(tmp_path):
    proc = _run_cli("--source", str(tmp_path / "nope"))

    assert proc.returncode == 2
    assert "does not exist" in proc.stderr


def test_cli_requires_source_argument(tmp_path):
    proc = _run_cli()
    assert proc.returncode == 2
    assert "the following arguments are required" in proc.stderr
