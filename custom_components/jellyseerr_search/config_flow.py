"""Config flow for Jellyseerr Search: one config entry per Jellyseerr server."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import JellyseerrAuthError, JellyseerrClient, JellyseerrConnectionError, JellyseerrError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)
REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


class JellyseerrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Connect to a Jellyseerr server with its API key."""

    VERSION = 1

    async def _async_validate(self, data: dict[str, Any]) -> str | None:
        """Return an error key, or None if the server accepted the key."""
        session = async_get_clientsession(self.hass, verify_ssl=data[CONF_VERIFY_SSL])
        client = JellyseerrClient(session, data[CONF_URL], data[CONF_API_KEY])
        try:
            await client.async_get_me()
        except JellyseerrAuthError:
            return "invalid_auth"
        except JellyseerrConnectionError:
            return "cannot_connect"
        except JellyseerrError:
            _LOGGER.exception("Unexpected answer from Jellyseerr")
            return "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**user_input, CONF_URL: _normalize_url(user_input[CONF_URL])}
            await self.async_set_unique_id(data[CONF_URL].lower())
            self._abort_if_unique_id_configured()
            if (error := await self._async_validate(data)) is None:
                return self.async_create_entry(title="Jellyseerr", data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            if (error := await self._async_validate(data)) is None:
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )
