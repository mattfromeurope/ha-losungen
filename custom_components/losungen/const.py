from __future__ import annotations

from typing import Final

DOMAIN: Final = "losungen"
NAME: Final = "Losungen"

BASE_URL: Final = (
    "https://www.losungen.de/fileadmin/media-losungen/download/Losung_{year}_XML.zip"
)
USER_AGENT: Final = "ha-losungen Home Assistant custom integration"

UPDATE_INTERVAL_MINUTES: Final = 30
REQUEST_TIMEOUT_SECONDS: Final = 60

MAX_STATE_LENGTH: Final = 255

ATTR_DATUM: Final = "datum"
ATTR_WOCHENTAG: Final = "wochentag"
ATTR_SONNTAG: Final = "sonntag"
ATTR_LOSUNGSTEXT: Final = "losungstext"
ATTR_LOSUNGSVERS: Final = "losungsvers"
ATTR_LEHRTEXT: Final = "lehrtext"
ATTR_LEHRTEXTVERS: Final = "lehrtextvers"
ATTR_TEXT_MARKDOWN: Final = "text_markdown"
