"""Card serving, Lovelace resource registration and version agreement."""

import json
from pathlib import Path

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from custom_components.jellyseerr_search.const import CARD_FILENAME, CARD_URL, CARD_VERSION, DOMAIN

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / DOMAIN


async def test_versions_agree() -> None:
    """The card's cache-busting check relies on all three matching."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())
    package = json.loads((INTEGRATION_DIR.parents[1] / "frontend" / "package.json").read_text())
    assert manifest["version"] == package["version"] == CARD_VERSION


async def test_bundle_is_built_for_this_version() -> None:
    bundle = (INTEGRATION_DIR / "frontend" / CARD_FILENAME).read_text()
    assert f'"{CARD_VERSION}"' in bundle


async def test_card_served_and_registered(hass: HomeAssistant, entry, hass_client) -> None:
    client = await hass_client()
    resp = await client.get(CARD_URL)
    assert resp.status == 200
    assert "jellyseerr-search-card" in await resp.text()
    ours = [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    ]
    assert [item["url"] for item in ours] == [f"{CARD_URL}?v={CARD_VERSION}"]
