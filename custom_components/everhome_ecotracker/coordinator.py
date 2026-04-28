"""Data coordinator for everHome EcoTracker cloud."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Protocol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EverHomeApiAuthError, EverHomeApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EverHomeDeviceApi(Protocol):
    """Protocol for everHome data sources."""

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return devices from the configured data source."""


class EverHomeDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Fetch everHome devices on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EverHomeDeviceApi,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data from everHome."""
        try:
            return await self.api.async_get_devices()
        except EverHomeApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except EverHomeApiError as err:
            raise UpdateFailed(str(err)) from err
