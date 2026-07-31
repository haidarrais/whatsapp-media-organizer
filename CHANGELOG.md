# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release.
- Core library that sorts WhatsApp media files (images, videos, voice notes)
  into a `YYYY/MM/DD` folder tree based on the date embedded in the filename.
- Supports both WhatsApp legacy names (`IMG-20231026-WA0001.jpg`) and the
  "media export" names (`WhatsApp Image 2025-07-09 at 13.52.37.jpeg`).
- `--dry-run` mode to preview moves without touching the filesystem.
- Collision resolution: renames colliding files with a numeric suffix, or
  skips them with `--no-rename`.
- Tkinter GUI for point-and-click use.
- Command-line interface installed as `whatsapp-media-organizer`.
- GitHub Actions CI with automated PyInstaller builds for Windows, macOS, and
  Linux on tagged releases.
