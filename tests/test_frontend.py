"""Card serving, Lovelace resource registration and version agreement."""

import json
from pathlib import Path
import re

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from custom_components.jellyseerr_search.const import (
    BROWSE_BRANDS,
    BROWSE_GENRES,
    CARD_FILENAME,
    CARD_URL,
    CARD_VERSION,
    DOMAIN,
)

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / DOMAIN


async def test_versions_agree() -> None:
    """The card's cache-busting check relies on all three matching."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())
    package = json.loads((INTEGRATION_DIR.parents[1] / "frontend" / "package.json").read_text())
    assert manifest["version"] == package["version"] == CARD_VERSION


def _card_table(name: str) -> dict[str, set[str]]:
    """A logic.ts table of { key, ..., types: [...] } rows, as key -> types."""
    logic = (INTEGRATION_DIR.parents[1] / "frontend" / "src" / "logic.ts").read_text()
    table = logic.split(f"export const {name}", 1)[1].split("];", 1)[0]
    return {
        key: set(re.findall(r'"(movie|tv)"', types))
        for key, types in re.findall(r'key: "(\w+)".*?types: \[([^\]]*)\]', table)
    }


def _server_table(table: dict) -> dict[str, set[str]]:
    return {key: {kind for kind, value in by_type.items() if value} for key, by_type in table.items()}


async def test_card_genres_match_the_server() -> None:
    """The card offers genres by key and says which types have them; the server
    must know the same keys and agree on the types, or a chip would fail."""
    assert _card_table("GENRES") == _server_table(BROWSE_GENRES)


async def test_card_brands_match_the_server() -> None:
    """Same for brands (Pixar has no TV filter, so the card says films only)."""
    assert _card_table("BRANDS") == _server_table(BROWSE_BRANDS)


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
