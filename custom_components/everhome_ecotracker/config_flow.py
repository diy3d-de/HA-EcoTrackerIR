"""Config flow for everHome EcoTracker."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EverHomeApiAuthError, EverHomeApiError, EverHomeCloudApi, EverHomeLocalApi
from .const import (
    CONF_AUTH_CODE,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_LOCAL_URL,
    CONF_REDIRECT_URI,
    CONF_SOURCE,
    CONF_TOKEN,
    DEFAULT_REDIRECT_URI,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
    SOURCE_CLOUD,
    SOURCE_LOCAL,
)

_LOGGER = logging.getLogger(__name__)

SOURCE_NAMES = {
    SOURCE_CLOUD: "everHome Cloud",
    SOURCE_LOCAL: "EcoTracker lokal",
}


def _source_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the source selection schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE,
                default=defaults.get(CONF_SOURCE, SOURCE_CLOUD),
            ): vol.In(SOURCE_NAMES),
        }
    )


def _cloud_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the cloud connection schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_CLIENT_ID,
                default=defaults.get(CONF_CLIENT_ID, ""),
            ): str,
            vol.Required(
                CONF_CLIENT_SECRET,
                default=defaults.get(CONF_CLIENT_SECRET, ""),
            ): str,
            vol.Required(
                CONF_REDIRECT_URI,
                default=defaults.get(CONF_REDIRECT_URI, DEFAULT_REDIRECT_URI),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            ): int,
        }
    )


def _local_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the local connection schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_LOCAL_URL,
                default=defaults.get(CONF_LOCAL_URL, ""),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            ): int,
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the options schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE,
                default=defaults.get(CONF_SOURCE, SOURCE_CLOUD),
            ): vol.In(SOURCE_NAMES),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            ): int,
        }
    )


class EverHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an everHome EcoTracker config flow."""

    VERSION = 1

    _connection_data: dict[str, Any]
    _oauth_state: str

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the data source."""
        if user_input is not None:
            if user_input[CONF_SOURCE] == SOURCE_LOCAL:
                return await self.async_step_local()
            return await self.async_step_cloud()

        return self.async_show_form(
            step_id="user",
            data_schema=_source_schema(user_input),
        )

    async def async_step_cloud(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect OAuth application data."""
        errors: dict[str, str] = {}

        if user_input is not None:
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            if not MIN_SCAN_INTERVAL_SECONDS <= scan_interval <= MAX_SCAN_INTERVAL_SECONDS:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                self._connection_data = {**user_input, CONF_SOURCE: SOURCE_CLOUD}
                self._oauth_state = secrets.token_urlsafe(16)
                return await self.async_step_authorize()

        return self.async_show_form(
            step_id="cloud",
            data_schema=_cloud_schema(user_input),
            errors=errors,
        )

    async def async_step_local(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect and validate local EcoTracker connection data."""
        errors: dict[str, str] = {}

        if user_input is not None:
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            if not MIN_SCAN_INTERVAL_SECONDS <= scan_interval <= MAX_SCAN_INTERVAL_SECONDS:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                try:
                    await self._async_validate_local_url(self.hass, user_input[CONF_LOCAL_URL])
                except EverHomeApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during local EcoTracker setup")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(
                        f"local_{EverHomeLocalApi.local_id(user_input[CONF_LOCAL_URL])}"
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="EcoTracker Lokal",
                        data={**user_input, CONF_SOURCE: SOURCE_LOCAL},
                    )

        return self.async_show_form(
            step_id="local",
            data_schema=_local_schema(user_input),
            errors=errors,
        )

    async def async_step_authorize(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Exchange the authorization code for an OAuth token."""
        errors: dict[str, str] = {}
        authorization_url = EverHomeCloudApi.authorization_url(
            self._connection_data[CONF_CLIENT_ID],
            self._connection_data[CONF_REDIRECT_URI],
            self._oauth_state,
        )

        if user_input is not None:
            code = user_input[CONF_AUTH_CODE].strip()
            session = async_get_clientsession(self.hass)
            try:
                token = await EverHomeCloudApi.async_exchange_code(
                    session,
                    self._connection_data[CONF_CLIENT_ID],
                    self._connection_data[CONF_CLIENT_SECRET],
                    code,
                    self._connection_data[CONF_REDIRECT_URI],
                )
                await self._async_validate_token(self.hass, token)
            except EverHomeApiAuthError:
                errors["base"] = "invalid_auth"
            except EverHomeApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during everHome setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(token.get("userid", "everhome")))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="everHome EcoTracker",
                    data={**self._connection_data, CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema({vol.Required(CONF_AUTH_CODE): str}),
            errors=errors,
            description_placeholders={"authorization_url": authorization_url},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth by starting a new authorization-code exchange."""
        self._connection_data = {
            CONF_SOURCE: SOURCE_CLOUD,
            CONF_CLIENT_ID: entry_data[CONF_CLIENT_ID],
            CONF_CLIENT_SECRET: entry_data[CONF_CLIENT_SECRET],
            CONF_REDIRECT_URI: entry_data[CONF_REDIRECT_URI],
            CONF_SCAN_INTERVAL: entry_data.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            ),
        }
        self._oauth_state = secrets.token_urlsafe(16)
        return await self.async_step_authorize()

    async def _async_validate_token(
        self,
        hass: HomeAssistant,
        token: dict[str, Any],
    ) -> None:
        """Validate the token by fetching the device list once."""
        api = EverHomeCloudApi(
            session=async_get_clientsession(hass),
            client_id=self._connection_data[CONF_CLIENT_ID],
            client_secret=self._connection_data[CONF_CLIENT_SECRET],
            token=token,
        )
        await api.async_get_devices()

    async def _async_validate_local_url(self, hass: HomeAssistant, local_url: str) -> None:
        """Validate a local EcoTracker URL."""
        api = EverHomeLocalApi(
            session=async_get_clientsession(hass),
            local_url=local_url,
        )
        await api.async_get_devices()

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return EverHomeOptionsFlow(config_entry)


class EverHomeOptionsFlow(config_entries.OptionsFlow):
    """Handle everHome EcoTracker options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._options_data: dict[str, Any] = {}

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        current_source = self._config_entry.options.get(
            CONF_SOURCE,
            self._config_entry.data.get(CONF_SOURCE, SOURCE_CLOUD),
        )
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        defaults = {
            CONF_SOURCE: current_source,
            CONF_SCAN_INTERVAL: current_interval,
        }

        if user_input is not None:
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            if not MIN_SCAN_INTERVAL_SECONDS <= scan_interval <= MAX_SCAN_INTERVAL_SECONDS:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            elif user_input[CONF_SOURCE] == SOURCE_LOCAL:
                self._options_data = user_input
                return await self.async_step_local_options()
            elif CONF_TOKEN not in self._config_entry.data:
                errors["base"] = "cloud_not_configured"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(defaults),
            errors=errors,
        )

    async def async_step_local_options(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage local EcoTracker options."""
        errors: dict[str, str] = {}
        current_url = self._config_entry.options.get(
            CONF_LOCAL_URL,
            self._config_entry.data.get(CONF_LOCAL_URL, ""),
        )

        if user_input is not None:
            try:
                api = EverHomeLocalApi(
                    session=async_get_clientsession(self.hass),
                    local_url=user_input[CONF_LOCAL_URL],
                )
                await api.async_get_devices()
            except EverHomeApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during local EcoTracker options")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="",
                    data={**self._options_data, CONF_LOCAL_URL: user_input[CONF_LOCAL_URL]},
                )

        return self.async_show_form(
            step_id="local_options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCAL_URL,
                        default=current_url,
                    ): str,
                }
            ),
            errors=errors,
        )
