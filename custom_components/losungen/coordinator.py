"""DataUpdateCoordinator: holt die Daten und verteilt sie an die Sensoren.

Der Coordinator ist das Bindeglied zwischen Netzwerk (api.py) und den Entities
(sensor.py): Home Assistant ruft _async_update_data() im Poll-Intervall auf;
die Sensoren lesen das Ergebnis aus coordinator.data und spiegeln
last_update_success in ihrer Verfügbarkeit.
"""

from __future__ import annotations

import logging
from datetime import timedelta

# timedelta beschreibt Zeitspannen (hier: das Poll-Intervall).

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# UpdateFailed signalisiert HA, dass ein Update fehlgeschlagen ist: Die Entities
# werden "unavailable" und HA versucht es beim nächsten Intervall erneut.

from homeassistant.util import dt as dt_util

# dt_util stellt Zeitzonen-Helfer bereit; dt_util.now() ist die aktuelle Zeit
# in der in HA konfigurierten Zeitzone (korrekt um Sommerzeit etc.).

from .api import LosungenAPIError, async_fetch_year
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES
from .parser import LosungDay

_LOGGER = logging.getLogger(__name__)


class LosungenCoordinator(DataUpdateCoordinator[dict[str, LosungDay]]):
    """Hält die Losungen des aktuellen Jahrgangs im Speicher.

    Das teure Herunterladen passiert nur, wenn der Cache den heutigen Tag nicht
    enthält (nach dem Start und nach Mitternacht); alle anderen Polls innerhalb
    eines Tages liefern den Cache ohne HTTP-Request.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        # super().__init__ initialisiert den Coordinator:
        #  - name=DOMAIN: Name in Logs und Diagnosedaten
        #  - update_interval: HA ruft _async_update_data() alle 30 Minuten auf
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        # Cache: {Jahr: {ISO-Datum: LosungDay}} – es wird nur das aktuelle Jahr
        # gehalten, damit der Speicher begrenzt bleibt.
        self._cache: dict[int, dict[str, LosungDay]] = {}

    async def _async_update_data(self) -> dict[str, LosungDay]:
        """Wird von HA bei jedem Poll aufgerufen; liefert {ISO-Datum: LosungDay}.

        Muss bei Erfolg die Daten zurückgeben; wirft es UpdateFailed, gelten
        alle Entities als nicht verfügbar, bis ein Poll wieder klappt.
        """
        # Lokaler Kalendertag in der HA-Zeitzone als ISO-String, z. B. "2026-11-23".
        # Das ist auch der Schlüssel, unter dem parser.py die Tage ablegt.
        today = dt_util.now().date().isoformat()
        year = int(today[:4])  # Jahr aus dem ISO-Datum, z. B. 2026
        cached = self._cache.get(year, {})
        if today in cached:
            # Heute schon geladen -> Cache zurückgeben, KEIN HTTP-Request.
            return cached
        try:
            # Jahres-Datei von losungen.de laden und parsen (nur 1x pro Tag nötig).
            data = await async_fetch_year(self.hass, year)
        except LosungenAPIError as err:
            # Download/Parsen fehlgeschlagen -> UpdateFailed (Entities unavailable,
            # nächster Poll versucht es erneut; beim allerersten Laden nach dem
            # Start wird daraus ConfigEntryNotReady mit automatischem Retry).
            raise UpdateFailed(f"Fehler beim Laden der Losungen: {err}") from err
        if today not in data:
            # Jahrgang geladen, aber heutiger Tag fehlt (sollte nicht vorkommen).
            raise UpdateFailed(f"Kein Eintrag für {today} in den Losungen gefunden")
        # Cache ersetzen (ältere Jahrgänge verwerfen).
        self._cache = {year: data}
        return data
