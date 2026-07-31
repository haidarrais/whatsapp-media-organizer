"""Unit tests for whatsapp_media_organizer.core."""

import zipfile

import pytest

from whatsapp_media_organizer.core import (
    extract_archive,
    extract_date,
    is_archive,
    is_valid_date,
    organize_whatsapp_media,
    unique_destination,
)


class TestExtractDate:
    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("IMG-20231026-WA0001.jpg", ("2023", "10", "26")),
            ("VID-20200101-WA0123.mp4", ("2020", "01", "01")),
            ("PTT-20240615-WA0009.opus", ("2024", "06", "15")),
            ("IMG-20231231-WA9999.jpeg", ("2023", "12", "31")),
            ("WhatsApp Image 2025-07-09 at 13.52.37.jpeg", ("2025", "07", "09")),
            ("WhatsApp Video 2024-11-30 at 08.00.00.mp4", ("2024", "11", "30")),
        ],
    )
    def test_matches_known_patterns(self, filename, expected):
        assert extract_date(filename) == expected

    @pytest.mark.parametrize(
        "filename",
        [
            "image.jpg",
            "WhatsApp Image at 13.52.37.jpeg",
            "notes.txt",
            "IMG-20231026.jpg",  # missing -WA suffix
        ],
    )
    def test_does_not_match(self, filename):
        assert extract_date(filename) is None


class TestIsValidDate:
    @pytest.mark.parametrize(
        "y,m,d",
        [
            ("2023", "10", "26"),
            ("2020", "01", "01"),
            ("2024", "02", "29"),
            ("2023", "12", "31"),
            ("1999", "05", "30"),
        ],
    )
    def test_valid_dates(self, y, m, d):
        assert is_valid_date(y, m, d)

    @pytest.mark.parametrize(
        "y,m,d",
        [
            ("2023", "00", "26"),
            ("2023", "13", "01"),
            ("2023", "10", "00"),
            ("2023", "10", "32"),
            ("2023", "02", "30"),
            ("2023", "04", "31"),
            ("not", "10", "26"),
            ("2023", "oct", "26"),
        ],
    )
    def test_invalid_dates(self, y, m, d):
        assert not is_valid_date(y, m, d)


class TestUniqueDestination:
    def test_returns_original_when_free(self, tmp_path):
        assert unique_destination(tmp_path, "photo.jpg") == tmp_path / "photo.jpg"

    def test_appends_suffix_on_collision(self, tmp_path):
        (tmp_path / "photo.jpg").write_text("a")
        (tmp_path / "photo_1.jpg").write_text("b")
        assert unique_destination(tmp_path, "photo.jpg") == tmp_path / "photo_2.jpg"

    def test_preserves_extension(self, tmp_path):
        (tmp_path / "clip.mp4").write_text("a")
        assert unique_destination(tmp_path, "clip.mp4") == tmp_path / "clip_1.mp4"


class TestOrganizeWhatsappMedia:
    def _make_source(self, tmp_path, names):
        src = tmp_path / "source"
        src.mkdir()
        for name in names:
            (src / name).write_text("x")
        return src

    def test_moves_files_into_yyyymmdd_tree(self, tmp_path):
        src = self._make_source(
            tmp_path, ["IMG-20231026-WA0001.jpg", "WhatsApp Image 2025-07-09 at 13.52.37.jpeg"]
        )
        dest = tmp_path / "dest"
        logs = []

        result = organize_whatsapp_media(src, dest, logs.append)

        assert result.moved == 2
        assert result.total == 2
        assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").is_file()
        assert (
            dest / "2025" / "07" / "09" / "WhatsApp Image 2025-07-09 at 13.52.37.jpeg"
        ).is_file()
        assert not (src / "IMG-20231026-WA0001.jpg").exists()
        assert len(logs) == 2

    def test_skips_unrecognized_files(self, tmp_path):
        src = self._make_source(tmp_path, ["notes.txt", "IMG-20231026-WA0001.jpg"])
        dest = tmp_path / "dest"

        result = organize_whatsapp_media(src, dest)

        assert result.moved == 1
        assert result.unrecognized == 1
        assert (src / "notes.txt").exists()
        assert result.skipped == 1

    def test_skips_impossible_dates(self, tmp_path):
        src = self._make_source(tmp_path, ["IMG-20230230-WA0001.jpg"])
        dest = tmp_path / "dest"

        result = organize_whatsapp_media(src, dest)

        assert result.unrecognized == 1
        assert result.moved == 0
        assert (src / "IMG-20230230-WA0001.jpg").exists()

    def test_renames_colliding_destination(self, tmp_path):
        src = self._make_source(tmp_path, ["IMG-20231026-WA0001.jpg"])
        dest = tmp_path / "dest"
        (dest / "2023" / "10" / "26").mkdir(parents=True)
        (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").write_text("existing")

        result = organize_whatsapp_media(src, dest)

        assert result.moved == 1
        assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001_1.jpg").is_file()

    def test_no_rename_skips_existing(self, tmp_path):
        src = self._make_source(tmp_path, ["IMG-20231026-WA0001.jpg"])
        dest = tmp_path / "dest"
        (dest / "2023" / "10" / "26").mkdir(parents=True)
        (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").write_text("existing")

        result = organize_whatsapp_media(src, dest, resolve_collisions=False)

        assert result.moved == 0
        assert result.skipped_existing == 1
        assert (src / "IMG-20231026-WA0001.jpg").exists()

    def test_logs_errors_for_unreadable_files(self, tmp_path, monkeypatch):
        src = self._make_source(tmp_path, ["IMG-20231026-WA0001.jpg"])
        dest = tmp_path / "dest"

        import shutil

        def broken_move(_src, _dst):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "move", broken_move)
        result = organize_whatsapp_media(src, dest)

        assert result.moved == 0
        assert len(result.errors) == 1
        assert "IMG-20231026-WA0001.jpg" in result.errors[0]

class TestIsArchive:
    @pytest.mark.parametrize(
        "filename",
        [
            "media.zip",
            "WhatsApp.zip",
            "archive.ZIP",
        ],
    )
    def test_detects_archives(self, filename):
        assert is_archive(filename)

    @pytest.mark.parametrize(
        "filename",
        [
            "media.zipx",
            "IMG-20231026-WA0001.jpg",
            "WhatsApp Video 2024-11-30 at 08.00.00.mp4",
            "archive.tar.gz",
        ],
    )
    def test_rejects_non_archives(self, filename):
        assert not is_archive(filename)


class TestExtractArchive:
    def _make_zip(self, tmp_path, name, members):
        path = tmp_path / name
        with zipfile.ZipFile(path, "w") as zf:
            for member_name, content in members:
                zf.writestr(member_name, content)
        return path

    def test_extracts_all_members(self, tmp_path):
        archive = self._make_zip(
            tmp_path,
            "media.zip",
            [
                ("IMG-20231026-WA0001.jpg", "a"),
                ("WhatsApp Image 2025-07-09 at 13.52.37.jpeg", "b"),
            ],
        )
        out = tmp_path / "out"
        out.mkdir()

        extracted = extract_archive(archive, out)

        assert set(extracted) == {
            out / "IMG-20231026-WA0001.jpg",
            out / "WhatsApp Image 2025-07-09 at 13.52.37.jpeg",
        }
        assert (out / "IMG-20231026-WA0001.jpg").read_text() == "a"
        assert (out / "WhatsApp Image 2025-07-09 at 13.52.37.jpeg").read_text() == "b"

    def test_does_not_escape_staging_directory(self, tmp_path):
        archive = self._make_zip(
            tmp_path,
            "evil.zip",
            [
                ("../../outside.txt", "nope"),
                ("/tmp/absolute.txt", "nope"),
                ("..\\windows-style.txt", "nope"),
            ],
        )
        out = tmp_path / "out"
        out.mkdir()

        extracted = extract_archive(archive, out)

        assert len(extracted) == 3
        assert (tmp_path / "outside.txt").exists() is False
        assert (tmp_path / "absolute.txt").exists() is False
        assert (tmp_path / "windows-style.txt").exists() is False
        for path in extracted:
            assert str(path).startswith(str(out))


class TestOrganizeArchives:
    def _make_zip(self, tmp_path, name, members):
        path = tmp_path / name
        with zipfile.ZipFile(path, "w") as zf:
            for member_name, content in members:
                zf.writestr(member_name, content)
        return path

    def test_extracts_and_sorts_archive_contents(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        archive = self._make_zip(
            src,
            "media.zip",
            [
                ("WhatsApp Image 2025-07-09 at 13.52.37.jpeg", "a"),
                ("IMG-20231026-WA0001.jpg", "b"),
                ("WhatsApp Video 2024-11-30 at 08.00.00.mp4", "c"),
            ],
        )
        dest = tmp_path / "dest"
        logs = []

        result = organize_whatsapp_media(src, dest, logs.append)

        assert result.moved == 3
        assert result.archives == 1
        assert (
            dest / "2025" / "07" / "09" / "WhatsApp Image 2025-07-09 at 13.52.37.jpeg"
        ).is_file()
        assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").is_file()
        assert (
            dest / "2024" / "11" / "30" / "WhatsApp Video 2024-11-30 at 08.00.00.mp4"
        ).is_file()
        assert not archive.exists()
        assert not any(log.startswith("Error") for log in logs)

    def test_archive_kept_when_member_fails_to_move(self, tmp_path, monkeypatch):
        src = tmp_path / "source"
        src.mkdir()
        archive = self._make_zip(
            src,
            "media.zip",
            [
                ("IMG-20231026-WA0001.jpg", "a"),
                ("WhatsApp Image 2025-07-09 at 13.52.37.jpeg", "b"),
            ],
        )
        dest = tmp_path / "dest"

        import shutil

        def broken_move(_src, _dst):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "move", broken_move)
        logs = []
        result = organize_whatsapp_media(src, dest, logs.append)

        assert result.moved == 0
        assert len(result.errors) == 2
        assert archive.exists()
        assert any("Kept archive" in message for message in logs)

    def test_archive_kept_when_member_unrecognized(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        archive = self._make_zip(
            src,
            "media.zip",
            [
                ("IMG-20231026-WA0001.jpg", "a"),
                ("notes.txt", "b"),
            ],
        )
        dest = tmp_path / "dest"

        result = organize_whatsapp_media(src, dest)

        assert result.moved == 1
        assert result.unrecognized == 1
        assert archive.exists()
        assert (dest / "2023" / "10" / "26" / "IMG-20231026-WA0001.jpg").is_file()

    def test_archive_kept_when_corrupt(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        archive = src / "broken.zip"
        archive.write_bytes(b"this is not a real zip")
        dest = tmp_path / "dest"

        result = organize_whatsapp_media(src, dest)

        assert len(result.errors) == 1
        assert "broken.zip" in result.errors[0]
        assert archive.exists()

    def test_no_extract_leaves_archive_untouched(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        archive = self._make_zip(src, "media.zip", [("IMG-20231026-WA0001.jpg", "a")])
        dest = tmp_path / "dest"

        result = organize_whatsapp_media(src, dest, extract_archives=False)

        assert result.moved == 0
        assert result.archives == 0
        assert archive.exists()

    def test_counts_only_files(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        (src / "nested").mkdir()
        (src / "IMG-20231026-WA0001.jpg").write_text("x")

        dest = tmp_path / "dest"
        result = organize_whatsapp_media(src, dest)

        assert result.total == 1
        assert result.moved == 1

    def test_missing_source_directory(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        with pytest.raises(FileNotFoundError):
            organize_whatsapp_media(missing, tmp_path / "dest")
