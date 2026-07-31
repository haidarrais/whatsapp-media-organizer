"""Core logic for organizing WhatsApp media files into a YYYY/MM/DD folder tree.

This module is deliberately dependency-free (standard library only) so it can be
reused by the CLI, the GUI, and tests alike.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# WhatsApp legacy short format: IMG-20231026-WA0001.jpg
_REGEX_SHORT = re.compile(r"^(?:IMG|VID|PTT)-(\d{4})(\d{2})(\d{2})-WA")
# WhatsApp "media" export format: WhatsApp Image 2025-07-09 at 13.52.37.jpeg
_REGEX_LONG = re.compile(r"^WhatsApp .* (\d{4})-(\d{2})-(\d{2})")
# Compressed archives that may hold WhatsApp media (e.g. Web/Desktop bulk downloads)
_ARCHIVE_SUFFIXES = (".zip",)


@dataclass
class OrganizeResult:
    """Summary of an organization run."""

    total: int = 0
    moved: int = 0
    skipped_existing: int = 0
    unrecognized: int = 0
    archives: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def skipped(self) -> int:
        """Files that were not moved (existing, unrecognized, or errors)."""
        return self.skipped_existing + self.unrecognized + len(self.errors)


def extract_date(filename: str) -> Optional[tuple[str, str, str]]:
    """Extract ``(year, month, day)`` from a WhatsApp media filename.

    Returns ``None`` when the filename does not match a known WhatsApp naming
    pattern. The caller is responsible for validating that the values are a
    plausible calendar date.
    """
    match = _REGEX_SHORT.search(filename) or _REGEX_LONG.search(filename)
    if match:
        return match.groups()  # type: ignore[return-value]
    return None


def is_valid_date(year: str, month: str, day: str) -> bool:
    """Return True when ``year``/``month``/``day`` form a real calendar date."""
    try:
        year_int = int(year)
        month_int = int(month)
        day_int = int(day)
    except ValueError:
        return False
    if not 1 <= month_int <= 12:
        return False
    # Days in each month for non-leap year; Feb+1 in leap years later
    max_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    max_day_for_month = max_days[month_int - 1]
    # Leap year check: divisible by 4, except centuries not divisible by 400
    if month_int == 2 and day_int > 29:
        return False
    if month_int == 2 and ((year_int % 4 == 0 and year_int % 100 != 0) or year_int % 400 == 0):
        max_day_for_month = 29
    if not 1 <= day_int <= max_day_for_month:
        return False
    return True


def is_archive(filename: str) -> bool:
    """Return True when ``filename`` looks like a supported compressed archive."""
    return filename.lower().endswith(_ARCHIVE_SUFFIXES)


def extract_archive(archive: Path, dest_dir: Path) -> list[Path]:
    """Extract ``archive`` into ``dest_dir`` and return the created file paths.

    Each member is extracted to a unique path inside ``dest_dir``, so archive
    entries can never escape the staging directory (path traversal protection).
    Directories are preserved implicitly by the member paths.
    """
    extracted: list[Path] = []
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = unique_destination(dest_dir, Path(member.filename).name)
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(target)
    return extracted


def unique_destination(dest_dir: Path, filename: str) -> Path:
    """Return a destination path that does not collide with an existing file.

    When ``dest_dir / filename`` already exists, a numeric suffix is appended
    before the extension (``photo.jpg`` -> ``photo_1.jpg``).
    """
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize_whatsapp_media(
    source_dir: str | os.PathLike[str],
    dest_dir: str | os.PathLike[str],
    log_callback: Optional[Callable[[str], None]] = None,
    *,
    resolve_collisions: bool = True,
    extract_archives: bool = True,
) -> OrganizeResult:
    """Move WhatsApp media files from ``source_dir`` into ``dest_dir/YYYY/MM/DD``.

    Files whose names match a known WhatsApp pattern are grouped by the date
    embedded in the name. Supported archives (``.zip``) are extracted into a
    temporary staging directory and their contents are organized the same way;
    an archive is deleted only when every file it contained was moved.
    ``log_callback`` is invoked for every notable event. Returns an
    :class:`OrganizeResult` describing what happened.

    Set ``resolve_collisions=False`` to skip (rather than rename) files that
    would overwrite an existing target. Set ``extract_archives=False`` to leave
    compressed archives untouched.
    """
    if log_callback is None:
        log_callback = lambda _msg: None  # noqa: E731

    src = Path(source_dir)
    dst = Path(dest_dir)
    dst.mkdir(parents=True, exist_ok=True)

    result = OrganizeResult()
    result.total = sum(1 for item in src.iterdir() if item.is_file())

    for item in sorted(item for item in src.iterdir() if item.is_file()):
        if is_archive(item.name) and extract_archives:
            _organize_archive(item, dst, result, log_callback, resolve_collisions)
            continue

        try:
            date = extract_date(item.name)
            if date is None or not is_valid_date(*date):
                result.unrecognized += 1
                log_callback(f"Skipped (Unrecognized format): {item.name}")
                continue

            year, month, day = date
            target_folder = dst / year / month / day
            target_folder.mkdir(parents=True, exist_ok=True)

            if resolve_collisions:
                target_path = unique_destination(target_folder, item.name)
            else:
                target_path = target_folder / item.name
                if target_path.exists():
                    result.skipped_existing += 1
                    log_callback(f"Skipped (Already exists): {item.name}")
                    continue

            shutil.move(str(item), str(target_path))
            result.moved += 1
            log_callback(
                f"Moved: {item.name} -> {year}{os.sep}{month}{os.sep}{day}{os.sep}"
            )
        except OSError as exc:
            result.errors.append(f"{item.name}: {exc}")
            log_callback(f"Error moving {item.name}: {exc}")

    return result


def _organize_archive(
    archive: Path,
    dst: Path,
    result: OrganizeResult,
    log_callback: Callable[[str], None],
    resolve_collisions: bool,
) -> None:
    """Extract ``archive``, organize its contents, and remove it when fully moved."""
    try:
        with tempfile.TemporaryDirectory(prefix="whatsapp-media-") as temp_dir:
            temp_path = Path(temp_dir)
            try:
                staged = extract_archive(archive, temp_path)
            except (OSError, zipfile.BadZipFile) as exc:
                raise OSError(f"cannot extract archive: {exc}") from exc

            if not staged:
                log_callback(f"Skipped (Empty archive): {archive.name}")
                return

            log_callback(f"Extracted: {archive.name} ({len(staged)} files)")
            before_moved = result.moved
            before_errors = len(result.errors)
            for staged_file in sorted(staged):
                try:
                    date = extract_date(staged_file.name)
                    if date is None or not is_valid_date(*date):
                        result.unrecognized += 1
                        log_callback(
                            f"Skipped (Unrecognized format): {archive.name} :: {staged_file.name}"
                        )
                        continue

                    year, month, day = date
                    target_folder = dst / year / month / day
                    target_folder.mkdir(parents=True, exist_ok=True)

                    if resolve_collisions:
                        target_path = unique_destination(target_folder, staged_file.name)
                    else:
                        target_path = target_folder / staged_file.name
                        if target_path.exists():
                            result.skipped_existing += 1
                            log_callback(
                                f"Skipped (Already exists): {archive.name} :: {staged_file.name}"
                            )
                            continue

                    shutil.move(str(staged_file), str(target_path))
                    result.moved += 1
                    log_callback(
                        f"Moved: {archive.name} :: {staged_file.name} "
                        f"-> {year}{os.sep}{month}{os.sep}{day}{os.sep}"
                    )
                except OSError as exc:
                    result.errors.append(f"{archive.name} :: {staged_file.name}: {exc}")
                    log_callback(
                        f"Error moving {archive.name} :: {staged_file.name}: {exc}"
                    )

            result.archives += 1
            all_moved = result.moved - before_moved == len(staged) and not (
                result.errors[before_errors:]
            )
            if all_moved:
                archive.unlink()
                log_callback(f"Deleted archive: {archive.name}")
            else:
                log_callback(
                    f"Kept archive (not fully organized): {archive.name}"
                )
    except OSError as exc:
        result.errors.append(f"{archive.name}: {exc}")
        log_callback(f"Error extracting {archive.name}: {exc}")
