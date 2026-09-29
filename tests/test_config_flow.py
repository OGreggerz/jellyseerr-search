"""Config flow tests."""

import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.jellyseerr_search.const import DOMAIN

from .common import API, COUNTS, DATA, URL, mock_entry


async def _start(hass: HomeAssistant, user_input: dict):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_create_entry(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/auth/me", json={"id": 1})
    aioclient_mock.get(f"{API}/request/count", json=COUNTS)
    # Bare host with trailing slash is normalized.
    result = await _start(hass, {**DATA, "url": "jellyseerr.local:5055/"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["url"] == URL
    assert aioclient_mock.mock_calls[0][3]["X-Api-Key"] == "secret"


async def test_invalid_auth(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/auth/me", status=401)
    result = await _start(hass, DATA)
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/auth/me", exc=aiohttp.ClientError)
    result = await _start(hass, DATA)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured(hass: HomeAssistant, aioclient_mock) -> None:
    mock_entry().add_to_hass(hass)
    result = await _start(hass, DATA)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, aioclient_mock) -> None:
    entry = mock_entry()
    entry.add_to_hass(hass)
    aioclient_mock.get(f"{API}/auth/me", json={"id": 1})
    aioclient_mock.get(f"{API}/request/count", json=COUNTS)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new-key"
