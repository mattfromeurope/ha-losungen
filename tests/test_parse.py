"""Tests für den reinen XML/ZIP-Parser (parser.py) – ganz OHNE Home Assistant.

parser.py importiert nur die Standardbibliothek, wird hier aber per importlib
aus dem Dateipfad geladen (nicht als Paket), damit der Test auch läuft, wenn
homeassistant nicht installiert ist. Das Modul muss vor dem Ausführen in
sys.modules registriert werden, sonst stolpert @dataclass in parser.py.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

# Absoluter Pfad zur parser.py im Repo.
PARSER_PATH = (
    Path(__file__).resolve().parent.parent / "custom_components" / "losungen" / "parser.py"
)
# Modul manuell aus der Datei laden:
spec = importlib.util.spec_from_file_location("losungen_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
# WICHTIG: Modul registrieren, BEVOR exec_module läuft (sonst schlägt @dataclass fehl).
sys.modules["losungen_parser"] = parser
spec.loader.exec_module(parser)

# Beispiel-XML im offiziellen Format: Wurzelelement + ein <Losungen>-Eintrag pro
# Tag mit den Feldern Datum, Wtag, Sonntag, Losungstext, Losungsvers, Lehrtext,
# Lehrtextvers. Der erste Eintrag nutzt ISO-Datum und Markup-Zeichen, der zweite
# das ältere TT.MM.JJJJ-Format.
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
    """Baut im Speicher eine ZIP wie die echte Download-Datei von losungen.de."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")  # str -> bytes (UTF-8 wie im echten XML)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(name, payload)  # die XML-Datei (Name wie im echten ZIP)
        zf.writestr("NUTZUNGSBEDINGUNGEN.pdf", b"%PDF-1.4 fake")  # Begleitdatei
    return buffer.getvalue()  # ZIP als Bytes


def test_parse_zip_returns_all_days() -> None:
    """Beide Tages-Einträge landen mit ISO-Datum als Schlüssel im dict."""
    days = parser.parse_losungen_zip(make_zip())
    assert set(days) == {"2026-11-23", "2026-11-24"}
    day = days["2026-11-23"]
    assert day.weekday == "Montag"
    assert day.sunday == "Letzter Sonntag des Kirchenjahres"
    assert day.losungsvers == "Jesaja 55,10-11"
    assert day.lehrtextvers == "Lukas 8,15"


def test_date_formats_normalized() -> None:
    """Auch das ältere Format TT.MM.JJJJ wird zu JJJJ-MM-TT normalisiert."""
    days = parser.parse_losungen_zip(make_zip())
    assert days["2026-11-24"].date == "2026-11-24"


def test_clean_text_strips_markup() -> None:
    """Markup-Zeichen (/ und #) werden entfernt, der Text bleibt erhalten."""
    days = parser.parse_losungen_zip(make_zip())
    assert days["2026-11-23"].losungstext == "So spricht der HERR: Ich will deinen Weg ..."
    # Der Rohtext bleibt für die Markdown-Ausgabe erhalten:
    assert days["2026-11-23"].losungstext_raw == "/So spricht der HERR:/ Ich will #deinen# Weg ..."


def test_markdown_text() -> None:
    """/.../ wird zu *...* (kursiv), #...# zu **...** (fett) für Markdown-Cards."""
    days = parser.parse_losungen_zip(make_zip())
    assert (
        parser.markdown_text(days["2026-11-23"].losungstext_raw)
        == "*So spricht der HERR:* Ich will **deinen** Weg ..."
    )


def test_bad_zip_raises() -> None:
    """Inhalt, der kein ZIP ist, wirft LosungenParseError."""
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_zip(b"not a zip")


def test_zip_without_xml_raises() -> None:
    """Eine ZIP ohne XML-Datei (z. B. nur PDF) wirft LosungenParseError."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "hello")
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_zip(buffer.getvalue())


def test_empty_xml_raises() -> None:
    """Gültiges XML ohne <Losungen>-Einträge wirft LosungenParseError."""
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_xml(b"<Losungsjahr></Losungsjahr>")


def test_invalid_xml_raises() -> None:
    """Kaputtes XML (abgeschnitten) wirft LosungenParseError."""
    with pytest.raises(parser.LosungenParseError):
        parser.parse_losungen_xml(b"<Losungsjahr>")
