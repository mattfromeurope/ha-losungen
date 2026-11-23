"""Parsing of the official Losungen XML files (stdlib only, no Home Assistant imports)."""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime


class LosungenParseError(Exception):
    """Raised when the downloaded Losungen data cannot be parsed."""


@dataclass(frozen=True)
class LosungDay:
    """One day of the Losungen year."""

    date: str
    weekday: str
    sunday: str
    losungstext: str
    losungsvers: str
    lehrtext: str
    lehrtextvers: str
    losungstext_raw: str
    lehrtext_raw: str


_SLASH_RE = re.compile(r"/([^/]*)/")
_HASH_RE = re.compile(r"#([^#]*)#")


def clean_text(raw: str) -> str:
    """Remove the /.../ and #...# markup characters, keep the enclosed text."""
    return _HASH_RE.sub(r"\1", _SLASH_RE.sub(r"\1", raw.strip()))


def markdown_text(raw: str) -> str:
    """Convert /.../ to *...* and #...# to **...** for use in markdown cards."""
    return _HASH_RE.sub(r"**\1**", _SLASH_RE.sub(r"*\1*", raw.strip()))


def normalize_date(raw: str) -> str:
    """Normalize <Datum> to ISO format (YYYY-MM-DD)."""
    raw = raw.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _text(node: ET.Element | None) -> str:
    return (node.text or "").strip() if node is not None else ""


def parse_losungen_xml(xml_data: bytes) -> dict[str, LosungDay]:
    """Parse the yearly XML, return a mapping ISO-date -> LosungDay."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as err:
        raise LosungenParseError(f"Invalid XML: {err}") from err

    days: dict[str, LosungDay] = {}
    for node in root.iter("Losungen"):
        date = normalize_date(_text(node.find("Datum")))
        if not date:
            continue
        losungstext_raw = _text(node.find("Losungstext"))
        lehrtext_raw = _text(node.find("Lehrtext"))
        days[date] = LosungDay(
            date=date,
            weekday=_text(node.find("Wtag")),
            sunday=_text(node.find("Sonntag")),
            losungstext=clean_text(losungstext_raw),
            losungsvers=_text(node.find("Losungsvers")),
            lehrtext=clean_text(lehrtext_raw),
            lehrtextvers=_text(node.find("Lehrtextvers")),
            losungstext_raw=losungstext_raw,
            lehrtext_raw=lehrtext_raw,
        )
    if not days:
        raise LosungenParseError("No <Losungen> entries found in XML")
    return days


def parse_losungen_zip(zip_data: bytes) -> dict[str, LosungDay]:
    """Extract the first XML file from the yearly download ZIP and parse it."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            names = [name for name in zf.namelist() if name.lower().endswith(".xml")]
            if not names:
                raise LosungenParseError("Download ZIP contains no XML file")
            return parse_losungen_xml(zf.read(names[0]))
    except zipfile.BadZipFile as err:
        raise LosungenParseError(f"Download is not a valid ZIP: {err}") from err
