"""Reiner Parser für die offiziellen Losungen-XML-Dateien.

Dieses Modul verwendet bewusst NUR die Python-Standardbibliothek (keinen
Home-Assistant-Import), damit es sich isoliert verstehen und testen lässt
(siehe tests/test_parse.py). Der Netzwerk-Teil liegt in api.py.
"""

from __future__ import annotations

# Standard-Einstieg in HA-Module: Typ-Annotationen werden nicht zur Laufzeit
# ausgewertet (siehe const.py).

import io

# io.BytesIO erzeugt ein In-Memory-"Datei"-Objekt aus Bytes; zipfile kann die
# ZIP direkt daraus lesen, ohne dass etwas auf die Platte geschrieben wird.

import re

# re = reguläre Ausdrücke; hier für die Markup-Zeichen in den Losungstexten.

import zipfile

# zipfile liest ZIP-Archive (die Jahres-Datei von losungen.de ist eine ZIP).

import xml.etree.ElementTree as ET

# ElementTree parst XML. Genutzt werden nur ET.fromstring() (Bytes -> Baum)
# sowie Element.iter()/find() (Navigation im Baum).

from dataclasses import dataclass

# @dataclass generiert automatisch __init__, __repr__ und __eq__ für die Klasse
# – spart Boilerplate bei reinen Datencontainern.

from datetime import datetime

# datetime.strptime wandelt Datums-Strings in echte Datumsobjekte um.


class LosungenParseError(Exception):
    """Wird geworfen, wenn die heruntergeladene Datei nicht ausgewertet werden kann.

    Von Exception abgeleitete eigene Fehlerklassen erlauben gezieltes Abfangen
    (except LosungenParseError) und landen als UpdateFailed im Coordinator.
    """


@dataclass(frozen=True)
class LosungDay:
    """Ein einzelner Tag des Losungen-Jahrgangs (Datencontainer).

    frozen=True macht das Objekt unveränderlich wie ein Tupel – nach dem Parsen
    sollen die Werte nicht versehentlich überschrieben werden.

    Felder:
      date:            ISO-Datum "JJJJ-MM-TT", z. B. "2026-11-23" (Schlüssel im dict)
      weekday:         Wochentag aus <Wtag>, z. B. "Montag"
      sunday:          liturgischer Sonntag aus <Sonntag>, z. B. "1. Advent" (oft leer)
      losungstext:     Text der Tageslosung OHNE Markup-Zeichen (bereinigt)
      losungsvers:     Bibelstelle der Losung, z. B. "Jesaja 55,10-11"
      lehrtext:        Text des Lehrtexts OHNE Markup-Zeichen (bereinigt)
      lehrtextvers:    Bibelstelle des Lehrtexts, z. B. "Lukas 8,15"
      losungstext_raw: Originaltext MIT Markup (z. B. "/Einleitung:/ Text #hervorgehoben#")
      lehrtext_raw:    Original-Lehrtext MIT Markup
    """

    date: str
    weekday: str
    sunday: str
    losungstext: str
    losungsvers: str
    lehrtext: str
    lehrtextvers: str
    losungstext_raw: str
    lehrtext_raw: str


# In den XML-Texten kennzeichnet "/.../" eine (kursiv darzustellende) Einleitung
# und "#...#" eine Hervorhebung. Diese beiden regulären Ausdrücke suchen solche
# Paare; ([^/]* bzw. [^#]*) ist die Klammergruppe mit dem eingeschlossenen Text.
_SLASH_RE = re.compile(r"/([^/]*)/")
_HASH_RE = re.compile(r"#([^#]*)#")


def clean_text(raw: str) -> str:
    """Entfernt die Markup-Zeichen / und #, behält aber den eingeschlossenen Text.

    Beispiel: "/So spricht der HERR:/ Ich will #deinen# Weg"
        ->    "So spricht der HERR: Ich will deinen Weg"
    """
    # .sub(r"\1", text) ersetzt jedes Vorkommen des Musters durch den Inhalt der
    # ersten Klammergruppe (\1) – also "/TEXT/" -> "TEXT" bzw. "#TEXT#" -> "TEXT".
    # raw.strip() entfernt führende/abschließende Leerzeichen und Zeilenumbrüche.
    return _HASH_RE.sub(r"\1", _SLASH_RE.sub(r"\1", raw.strip()))


def markdown_text(raw: str) -> str:
    """Wandelt die Markup-Zeichen in Markdown um: /.../ -> *...* und #...# -> **...**.

    So kann der Text direkt in einer Markdown-Card ausgegeben werden (kursiv
    bzw. fett), ohne dass die rohen Markupzeichen sichtbar wären.
    """
    # Gleiches Prinzip wie clean_text, nur werden die Klammergruppen in
    # Markdown-Sterne gewickelt statt entfernt.
    return _HASH_RE.sub(r"**\1**", _SLASH_RE.sub(r"*\1*", raw.strip()))


def normalize_date(raw: str) -> str:
    """Normalisiert das <Datum>-Feld auf ISO-Format "JJJJ-MM-TT".

    Die XML der Brüder-Unität nutzt "JJJJ-MM-TT", ältere Jahrgänge teils
    "TT.MM.JJJJ". raw[:10] schneidet eine ggf. angehängte Uhrzeit ab
    (z. B. "2026-11-23T00:00:00" -> "2026-11-23").
    """
    raw = raw.strip()[:10]
    # Beide möglichen Formate nacheinander probieren:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            # strptime parst den String zum Datum; .date() nimmt den Datumsteil;
            # .isoformat() liefert wieder "JJJJ-MM-TT".
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            # Dieses Format passt nicht auf den String -> nächster Versuch.
            continue
    # Unbekanntes Format: gekürzten Rohwert zurückgeben (besser als Absturz).
    return raw


def _text(node: ET.Element | None) -> str:
    """Hilfsfunktion: Text eines XML-Elements, oder "" wenn das Element fehlt.

    node.find(...) liefert None, wenn es kein Kindelement mit diesem Namen gibt;
    (node.text or "") fängt sowohl None als auch leere Elemente (<Sonntag></Sonntag>)
    ab. .strip() entfernt Whitespace am Rand.
    """
    return (node.text or "").strip() if node is not None else ""


def parse_losungen_xml(xml_data: bytes) -> dict[str, LosungDay]:
    """Parst die Jahres-XML und gibt ein dict {ISO-Datum: LosungDay} zurück.

    Aufbau der Datei: Ein Wurzelelement, darunter pro Tag ein Element <Losungen>
    mit den Kindelementen <Datum>, <Wtag>, <Sonntag>, <Losungstext>, <Losungsvers>,
    <Lehrtext>, <Lehrtextvers>.
    """
    try:
        # ET.fromstring wandelt die XML-Bytes in den Wurzel-Elementbaum um.
        root = ET.fromstring(xml_data)
    except ET.ParseError as err:
        # Ungültiges XML (z. B. eine HTML-Fehlerseite statt der Datei).
        raise LosungenParseError(f"Ungültiges XML: {err}") from err

    days: dict[str, LosungDay] = {}
    # root.iter("Losungen") liefert ALLE Elemente namens <Losungen> im Baum –
    # das sind genau die Tages-Einträge, unabhängig vom Namen des Wurzelelements.
    for node in root.iter("Losungen"):
        date = normalize_date(_text(node.find("Datum")))
        if not date:
            continue  # Eintrag ohne Datum überspringen (kommt praktisch nicht vor)
        # Rohtexte merken (für die Markdown-Variante) und bereinigte Fassungen speichern.
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
        # Leere/unerwartete Datei -> klarer Fehler statt stiller leerer Sensoren.
        raise LosungenParseError("Keine <Losungen>-Einträge in der XML gefunden")
    return days


def parse_losungen_zip(zip_data: bytes) -> dict[str, LosungDay]:
    """Entpackt die heruntergeladene ZIP und parst die darin enthaltene XML-Datei."""
    try:
        # ZipFile liest das Archiv aus dem BytesIO-Objekt; der Kontextmanager
        # (with) schließt die Datei wieder sauber.
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Die ZIP enthält die XML plus die Nutzungsbedingungen (PDF); wir nehmen
            # die erste Datei mit der Endung .xml (Groß-/Kleinschreibung egal).
            names = [name for name in zf.namelist() if name.lower().endswith(".xml")]
            if not names:
                raise LosungenParseError("Download-ZIP enthält keine XML-Datei")
            # zf.read(name) liefert den Dateiinhalt als Bytes -> an den XML-Parser.
            return parse_losungen_xml(zf.read(names[0]))
    except zipfile.BadZipFile as err:
        # z. B. HTML-Fehlerseite, die als ZIP getarnt heruntergeladen wurde.
        raise LosungenParseError(f"Download ist kein gültiges ZIP: {err}") from err
