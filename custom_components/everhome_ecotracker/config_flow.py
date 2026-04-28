"""Config flow for everHome EcoTracker cloud."""

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

from .api import EverHomeApi, EverHomeApiAuthError, EverHomeApiError
from .const import (
    CONF_AUTH_CODE,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REDIRECT_URI,
    CONF_TOKEN,
    DEFAULT_REDIRECT_URI,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _connection_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
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


class EverHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an everHome EcoTracker config flow."""

    VERSION = 1

    _connection_data: dict[str, Any]
    _oauth_state: str

    async def async_step_user(
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
                self._connection_data = user_input
                self._oauth_state = secrets.token_urlsafe(16)
                return await self.async_step_authorize()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input),
            errors=errors,
        )

    async def async_step_authorize(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Exchange the authorization code for an OAuth token."""
        errors: dict[str, str] = {}
        authorization_url = EverHomeApi.authorization_url(
            self._connection_data[CONF_CLIENT_ID],
            self._connection_data[CONF_REDIRECT_URI],
            self._oauth_state,
        )

        if user_input is not None:
            code = user_input[CONF_AUTH_CODE].strip()
            session = async_get_clientsession(self.hass)
            try:
                token = await EverHomeApi.async_exchange_code(
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
        api = EverHomeApi(
            session=async_get_clientsession(hass),
            client_id=self._connection_data[CONF_CLIENT_ID],
            client_secret=self._connection_data[CONF_CLIENT_SECRET],
            token=token,
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

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
        )

        if user_input is not None:
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            if not MIN_SCAN_INTERVAL_SECONDS <= scan_interval <= MAX_SCAN_INTERVAL_SECONDS:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): int,
                }
            ),
            errors=errors,
        )
