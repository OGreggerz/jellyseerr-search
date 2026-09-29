"""Shared fixtures."""

import pytest

from homeassistant.core import HomeAssistant

from .common import API, COUNTS, mock_entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA load custom_components/ in every test."""
    yield


@pytest.fixture
async def entry(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(f"{API}/request/count", json=COUNTS)
    entry = mock_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
