"""HTTP-Zugriff auf losungen.de.

Dieses Modul ist die EINZIGE Stelle der Integration, die Netzwerkzugriff hat:
Es lädt die Jahres-ZIP herunter und delegiert Entpacken/Parsen an parser.py.
"""

from __future__ import annotations

import asyncio

# asyncio stellt u. a. asyncio.timeout bereit (ab Python 3.11).

import logging

# logging ist das Standard-Logging von Python; HA zeigt diese Einträge in
# home-assistant.log an.

import aiohttp

# aiohttp ist der HTTP-Client von Home Assistant (asynchron).

from homeassistant.core import HomeAssistant

from homeassistant.helpers.aiohttp_client import async_get_clientsession

# async_get_clientsession liefert die gemeinsame aiohttp-Session von HA:
# SSL-Kontext, Connection-Pooling und Timeouts werden mit allen anderen
# Integrationen geteilt – nie eine eigene aiohttp.ClientSession() erzeugen.

from .const import BASE_URL, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from .parser import LosungDay, LosungenParseError, parse_losungen_zip

_LOGGER = logging.getLogger(__name__)
# Logger dieses Moduls; der Name entspricht dem Modulpfad.


class LosungenAPIError(Exception):
    """Basisklasse für alle Fehler beim Abruf der Losungen."""


class LosungenConnectionError(LosungenAPIError):
    """Der Download von losungen.de ist fehlgeschlagen (Netzwerk, 404, Timeout)."""


# __all__ legt fest, welche Namen bei `from .api import *` exportiert werden.
__all__ = [
    "LosungenAPIError",
    "LosungenConnectionError",
    "LosungenParseError",  # re-exportiert aus parser.py, praktisch für Aufrufer
    "LosungDay",  # re-exportiert aus parser.py
    "async_fetch_year",
]


async def async_fetch_year(hass: HomeAssistant, year: int) -> dict[str, LosungDay]:
    """Lädt und parst die Losungen des übergebenen Jahres.

    Ablauf:
      1. URL aus BASE_URL bauen (Jahr einsetzen).
      2. GET-Request über die gemeinsame HA-aiohttp-Session senden.
      3. Antwort-Body lesen und im Executor-Thread entpacken/parsen, weil
         zipfile/ElementTree blockierende (synchrone) Arbeit sind – im
         Async-Eventloop von HA dürfen keine blockierenden Aufrufe laufen.

    Rückgabe: dict {ISO-Datum: LosungDay} für das ganze Jahr.
    """
    session = async_get_clientsession(hass)
    url = BASE_URL.format(year=year)
    try:
        # asyncio.timeout beendet den gesamten Block nach N Sekunden mit
        # TimeoutError – ein hängender Server blockiert so nicht HA.
        async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
            # GET-Request; await wartet asynchron auf die Antwort.
            response = await session.get(url, headers={"User-Agent": USER_AGENT})
            if response.status == 404:
                # z. B. Jahres-Datei (noch) nicht veröffentlicht.
                raise LosungenConnectionError(
                    f"Keine Losungen-Datei für Jahr {year} (404)"
                )
            # raise_for_status() wirft bei HTTP-Fehlercodes (500 etc.)
            # eine aiohttp.ClientResponseError (eine Unterklasse von ClientError).
            response.raise_for_status()
            # Body komplett als Bytes einlesen (die ZIP ist klein, ca. 1 MB).
            payload = await response.read()
    except LosungenAPIError:
        # eigene Fehler unverändert weiterreichen
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        # Netzwerk-/HTTP-Fehler in unseren Fehlertyp kapseln (mit Originalfehler
        # als __cause__ via "from err").
        raise LosungenConnectionError(f"Fehler beim Laden von {url}: {err}") from err

    # Blockierende Arbeit (ZIP öffnen, XML parsen) in einen Worker-Thread
    # auslagern; async_add_executor_job liefert ein awaitable Ergebnis.
    return await hass.async_add_executor_job(parse_losungen_zip, payload)
