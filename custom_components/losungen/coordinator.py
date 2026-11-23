from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import LosungenAPIError, async_fetch_year
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES
from .parser import LosungDay

_LOGGER = logging.getLogger(__name__)


class LosungenCoordinator(DataUpdateCoordinator[dict[str, LosungDay]]):
    """Keeps the Losungen of the current year in memory.

    The yearly file is downloaded once; while the calendar day does not change,
    updates are served from the cache without any HTTP request.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self._cache: dict[int, dict[str, LosungDay]] = {}

    async def _async_update_data(self) -> dict[str, LosungDay]:
        today = dt_util.now().date().isoformat()
        year = int(today[:4])
        cached = self._cache.get(year, {})
        if today in cached:
            return cached
        try:
            data = await async_fetch_year(self.hass, year)
        except LosungenAPIError as err:
            raise UpdateFailed(f"Error fetching Losungen: {err}") from err
        if today not in data:
            raise UpdateFailed(f"No Losung found for {today}")
        self._cache = {year: data}
        return data
