"""Make ``python -m whatsapp_media_organizer`` work from anywhere."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
