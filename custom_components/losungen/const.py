"""Konstanten der Integration `losungen`.

Alle zentralen Werte (Domain, URLs, Attributnamen), die an mehreren Stellen
gebraucht werden, liegen hier an genau einer Stelle, damit sie leicht
auffindbar und änderbar sind.
"""

from __future__ import annotations

# Dieser Import macht alle Typ-Annotationen im Modul "faul": Sie werden nicht
# zur Laufzeit ausgewertet, sondern nur von Typcheckern gelesen. Dadurch dürfen
# Typen auch "vorwärts" referenziert werden (z. B. eine Klasse, die später im
# selben Modul definiert wird).

from typing import Final

# `Final` markiert Werte als Konstanten: Per Konvention werden sie nicht mehr
# verändert; Typchecker (mypy/pyright) melden eine Warnung, falls doch.

# Die Domain ist der technische Name der Integration. Sie MUSS exakt dem
# Verzeichnisnamen unter custom_components/ entsprechen und wird in HA überall
# als Präfix verwendet (Config Entry, eindeutige IDs, Log-Einträge ...).
DOMAIN: Final = "losungen"

# Anzeigename des Geräts in Home Assistant (taucht als Gerätename auf).
NAME: Final = "Losungen"

# URL der offiziellen Jahres-Datei der Evangelischen Brüder-Unität.
# "{year}" wird per str.format(year=...) durch das jeweilige Jahr ersetzt, z. B.
# https://www.losungen.de/fileadmin/media-losungen/download/Losung_2026_XML.zip
# Die ZIP enthält eine XML-Datei ("Losungen Free <Jahr>.xml") mit allen Tagen
# des Jahrgangs (Losungstext, Losungsvers, Lehrtext, Lehrtextvers, Datum, ...).
BASE_URL: Final = (
    "https://www.losungen.de/fileadmin/media-losungen/download/Losung_{year}_XML.zip"
)

# Kennung, mit der sich unsere HTTP-Anfragen bei losungen.de ausweisen.
USER_AGENT: Final = "ha-losungen Home Assistant custom integration"

# Poll-Intervall des Coordinators in Minuten. Da die Daten pro Tag gecacht
# werden (siehe coordinator.py), ist das Intervall nur dafür da, den
# Tageswechsel (Mitternacht) zeitnah mitzubekommen – ohne dass ständig
# geladen wird.
UPDATE_INTERVAL_MINUTES: Final = 30

# Timeout für den HTTP-Download in Sekunden (hängender Server soll HA nicht
# blockieren).
REQUEST_TIMEOUT_SECONDS: Final = 60

# Home Assistant begrenzt Sensor-States auf 255 Zeichen ( Datenbank-Limit).
# Längere Texte (z. B. Lehrtexte) werden im State gekürzt; der volle Text steht
# immer in den Attributen (siehe sensor.py).
MAX_STATE_LENGTH: Final = 255

# Namen der Attribute, die die Sensoren zusätzlich zum State tragen
# (siehe sensor.py: extra_state_attributes). Einheitlich hier definiert, damit
# Templates und Code dieselben Namen verwenden.
ATTR_DATUM: Final = "datum"
ATTR_WOCHENTAG: Final = "wochentag"
ATTR_SONNTAG: Final = "sonntag"
ATTR_LOSUNGSTEXT: Final = "losungstext"
ATTR_LOSUNGSVERS: Final = "losungsvers"
ATTR_LEHRTEXT: Final = "lehrtext"
ATTR_LEHRTEXTVERS: Final = "lehrtextvers"
ATTR_TEXT_MARKDOWN: Final = "text_markdown"
