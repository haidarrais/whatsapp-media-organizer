"""Command-line interface for the WhatsApp Media Organizer."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .core import organize_whatsapp_media
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whatsapp-media-organizer",
        description=(
            "Sort WhatsApp media files into a YYYY/MM/DD folder structure based "
            "on the date embedded in each filename."
        ),
        epilog=(
            "examples:\n"
            "  whatsapp-media-organizer --source ~/Downloads/WhatsApp --dest ~/sorted\n"
            "  whatsapp-media-organizer --source ~/Downloads/WhatsApp --dest ~/sorted --no-rename\n"
            "  whatsapp-media-organizer --source ~/Downloads/WhatsApp --dest ~/sorted --dry-run\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        "-s",
        type=Path,
        help="Directory containing the WhatsApp media files to organize.",
    )
    parser.add_argument(
        "--dest",
        "-d",
        type=Path,
        default=Path.home() / "Desktop" / "sorted_media",
        help=(
            "Destination root directory. Files are placed under "
            "YYYY/MM/DD subfolders. Default: ~/Desktop/sorted_media."
        ),
    )
    parser.add_argument(
        "--no-rename",
        action="store_true",
        help="Skip files whose destination already exists instead of renaming them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without touching the filesystem.",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help=(
            "Leave compressed archives (e.g. .zip) untouched instead of "
            "extracting and sorting their contents."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _dry_run(source: Path, extract_archives: bool = True) -> int:
    import zipfile

    from .core import extract_archive, extract_date, is_archive, is_valid_date

    total = moved = 0
    for item in sorted(item for item in source.iterdir() if item.is_file()):
        if is_archive(item.name):
            if not extract_archives:
                print(f"would skip : {item.name} (--no-extract)")
                continue
            total += 1
            try:
                with tempfile.TemporaryDirectory(prefix="whatsapp-media-") as temp_dir:
                    staged = extract_archive(item, Path(temp_dir))
                    for staged_file in sorted(staged):
                        date = extract_date(staged_file.name)
                        if date is None or not is_valid_date(*date):
                            print(
                                f"would skip : {item.name} :: {staged_file.name} "
                                "(unrecognized format)"
                            )
                            continue
                        year, month, day = date
                        moved += 1
                        print(
                            f"would move : {item.name} :: {staged_file.name} "
                            f"-> {year}/{month}/{day}/"
                        )
            except (OSError, zipfile.BadZipFile) as exc:
                print(f"would skip : {item.name} (error reading archive: {exc})")
            continue
        total += 1
        date = extract_date(item.name)
        if date is None or not is_valid_date(*date):
            print(f"would skip : {item.name} (unrecognized format)")
            continue
        year, month, day = date
        moved += 1
        print(f"would move : {item.name} -> {year}/{month}/{day}/")
    print(f"\nWould move {moved} of {total} files.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.source is None:
        build_parser().error("the following arguments are required: --source/-s")

    source = args.source.expanduser()
    dest = args.dest.expanduser()

    if not source.is_dir():
        print(f"error: source directory does not exist: {source}", file=sys.stderr)
        return 2

    if args.dry_run:
        return _dry_run(source, extract_archives=not args.no_extract)

    def log(message: str) -> None:
        print(message)

    result = organize_whatsapp_media(
        source,
        dest,
        log,
        resolve_collisions=not args.no_rename,
        extract_archives=not args.no_extract,
    )

    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)

    if result.moved == 0 and result.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
