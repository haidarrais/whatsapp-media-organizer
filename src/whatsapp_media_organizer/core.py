"""Core logic for organizing WhatsApp media files into a YYYY/MM/DD folder tree.

This module is deliberately dependency-free (standard library only) so it can be
reused by the CLI, the GUI, and tests alike.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Pattern

# WhatsApp legacy short format: IMG-20231026-WA0001.jpg
_REGEX_SHORT = re.compile(r"^(?:IMG|VID|PTT)-(\d{4})(\d{2})(\d{2})-WA")
# WhatsApp "media" export format: WhatsApp Image 2025-07-09 at 13.52.37.jpeg
_REGEX_LONG = re.compile(r"^WhatsApp .* (\d{4})-(\d{2})-(\d{2})")


@dataclass
class OrganizeResult:
    """Summary of an organization run."""

    total: int = 0
    moved: int = 0
    skipped_existing: int = 0
    unrecognized: int = 0
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
        _ = int(year)
        month_int = int(month)
        day_int = int(day)
    except ValueError:
        return False
    if not 1 <= month_int <= 12:
        return False
    if not 1 <= day_int <= 31:
        return False
    # Quick sanity check without pulling in the calendar module: reject 2/30,
    # 4/31, 6/31, 9/31, 11/31-style impossibilities.
    if day_int > 30 and month_int in (2, 4, 6, 9, 11):
        return False
    return True


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
) -> OrganizeResult:
    """Move WhatsApp media files from ``source_dir`` into ``dest_dir/YYYY/MM/DD``.

    Files whose names match a known WhatsApp pattern are grouped by the date
    embedded in the name. ``log_callback`` is invoked for every notable event.
    Returns an :class:`OrganizeResult` describing what happened.

    Set ``resolve_collisions=False`` to skip (rather than rename) files that
    would overwrite an existing target.
    """
    if log_callback is None:
        log_callback = lambda _msg: None  # noqa: E731

    src = Path(source_dir)
    dst = Path(dest_dir)
    dst.mkdir(parents=True, exist_ok=True)

    result = OrganizeResult()
    result.total = sum(1 for item in src.iterdir() if item.is_file())

    for item in src.iterdir():
        if not item.is_file():
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
