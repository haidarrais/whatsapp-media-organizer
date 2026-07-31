"""PyInstaller entry point for the packaged CLI binary."""

from whatsapp_media_organizer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
