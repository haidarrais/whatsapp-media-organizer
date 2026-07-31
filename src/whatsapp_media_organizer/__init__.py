"""WhatsApp Media Organizer - sort WhatsApp media into a YYYY/MM/DD folder tree."""

from .core import (
    OrganizeResult,
    extract_date,
    is_valid_date,
    organize_whatsapp_media,
    unique_destination,
)
from .version import __version__

__all__ = [
    "OrganizeResult",
    "__version__",
    "extract_date",
    "is_valid_date",
    "organize_whatsapp_media",
    "unique_destination",
]
