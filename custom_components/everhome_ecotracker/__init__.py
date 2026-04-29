"""everHome EcoTracker cloud integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EverHomeApiError, EverHomeCloudApi, EverHomeLocalApi
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_LOCAL_URL,
    CONF_REDIRECT_URI,
    CONF_SOURCE,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    SOURCE_CLOUD,
    SOURCE_LOCAL,
)
from .coordinator import EverHomeDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up everHome EcoTracker from a config entry."""

    async def async_update_token(token: dict) -> None:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_TOKEN: token},
        )

    session = async_get_clientsession(hass)
    source = entry.options.get(CONF_SOURCE, entry.data.get(CONF_SOURCE, SOURCE_CLOUD))
    if source == SOURCE_LOCAL:
        local_url = entry.options.get(CONF_LOCAL_URL) or entry.data.get(CONF_LOCAL_URL)
        if not local_url:
            raise ConfigEntryNotReady("Local EcoTracker URL is missing")
        api = EverHomeLocalApi(
            session=session,
            local_url=local_url,
        )
    else:
        api = EverHomeCloudApi(
            session=session,
            client_id=entry.data[CONF_CLIENT_ID],
            client_secret=entry.data[CONF_CLIENT_SECRET],
            token=dict(entry.data[CONF_TOKEN]),
            token_updater=async_update_token,
        )

    scan_interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
    )
    coordinator = EverHomeDataUpdateCoordinator(
        hass,
        api,
        update_interval=timedelta(seconds=scan_interval_seconds),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except EverHomeApiError as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an everHome EcoTracker config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload an everHome EcoTracker config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
