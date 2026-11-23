"""Tests for the pure XML/ZIP parser (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

PARSER_PATH = (
    Path(__file__).resolve().parent.parent / "custom_components" / "losungen" / "parser.py"
)
spec = importlib.util.spec_from_file_location("losungen_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules["losungen_parser"] = parser
spec.loader.exec_module(parser)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Losungsjahr>
  <Losungen>
    <Datum>2026-11-23</Datum>
    <Wtag>Montag</Wtag>
    <Sonntag>Letzter Sonntag des Kirchenjahres</Sonntag>
    <Losungstext>/So spricht der HERR:/ Ich will #deinen# Weg ...</Losungstext>
    <Losungsvers>Jesaja 55,10-11</Losungsvers>
    <Lehrtext>Gleichwie der Regen und Schnee vom Himmel fällt.</Lehrtext>
    <Lehrtextvers>Lukas 8,15</Lehrtextvers>
  </Losungen>
  <Losungen>
    <Datum>24.11.2026</Datum>
    <Wtag>Dienstag</Wtag>
    <Sonntag></Sonntag>
    <Losungstext>Der HERR ist mein Hirte.</Losungstext>
    <Losungsvers>Psalm 23,1</Losungsvers>
    <Lehrtext>Ich bin der gute Hirte.</Lehrtext>
    <Lehrtextvers>Johannes 10,11</Lehrtextvers>
  </Losungen>
</Losungsjahr>
"""


def make_zip(payload: bytes | str = SAMPLE_XML, name: str = "Losungen Free 2026.xml") -> bytes:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(name, payload)
        zf.writestr("NUTZUNGSBEDINGUNGEN.pdf", b"%PDF-1.4 fake")
    return buffer.getvalue()


def test_parse_zip_returns_all_days() -> None:
    days = parser.parse_losungen_zip(make_zip())
    assert set(days) == {"2026-11-23", "2026-11-24"}
    day = days["2026-11-23"]
    assert day.weekday == "Montag"
    assert day.sunday == "Letzter Sonntag des Kirchenjahres"
    assert day.losungsvers == "Jesaja 55,10-11"
    assert day.lehrtextvers == "Lukas 8,15"


def test_date_formats_normalized() -> None:
    days = parser.parse_losungen_zip(make_zip())
    assert days["2026-11-24"].date == "2026-11-24"


def test_clean_text_strips_markup() -> None:
    days = parser.parse_losungen_zip(make_zip())
    assert days["2026-11-23"].losungstext == "So spricht der HERR: Ich will deinen Weg ..."
    assert days["2026-11-23"].losungstext_raw == "/So spricht der HERR:/ Ich will #deinen# Weg ..."


def test_markdown_text() -> None:
    days = parser.parse_losungen_zip(make_zip())
    assert (
        parser.markdown_text(days["2026-11-23"].losungstext_raw)
        == "*So spricht der HERR:* Ich will **deinen** Weg ..."
    )


def test_bad_zip_raises() -> None:
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_zip(b"not a zip")


def test_zip_without_xml_raises() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "hello")
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_zip(buffer.getvalue())


def test_empty_xml_raises() -> None:
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_xml(b"<Losungsjahr></Losungsjahr>")


def test_invalid_xml_raises() -> None:
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_xml(b"<Losungsjahr>")
