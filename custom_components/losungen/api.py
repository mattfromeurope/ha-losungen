from __future__ import annotations

import asyncio
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import BASE_URL, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from .parser import LosungDay, LosungenParseError, parse_losungen_zip

_LOGGER = logging.getLogger(__name__)


class LosungenAPIError(Exception):
    """Base error for fetching the Losungen."""


class LosungenConnectionError(LosungenAPIError):
    """Raised when the download from losungen.de fails."""


__all__ = [
    "LosungenAPIError",
    "LosungenConnectionError",
    "LosungenParseError",
    "LosungDay",
    "async_fetch_year",
]


async def async_fetch_year(hass: HomeAssistant, year: int) -> dict[str, LosungDay]:
    """Download and parse the official Losungen XML for the given year."""
    session = async_get_clientsession(hass)
    url = BASE_URL.format(year=year)
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
            response = await session.get(url, headers={"User-Agent": USER_AGENT})
            if response.status == 404:
                raise LosungenConnectionError(f"No Losungen file for year {year} (404)")
            response.raise_for_status()
            payload = await response.read()
    except LosungenAPIError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        raise LosungenConnectionError(f"Error fetching {url}: {err}") from err

    return await hass.async_add_executor_job(parse_losungen_zip, payload)
