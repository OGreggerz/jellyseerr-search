"""WebSocket commands used by the card."""

from homeassistant.core import HomeAssistant

from custom_components.jellyseerr_search.const import CARD_VERSION, DOMAIN

from .common import API, SEARCH

TV = {
    "id": 90228,
    "seasons": [
        {"seasonNumber": 0, "name": "Specials", "episodeCount": 3},
        {"seasonNumber": 1, "name": "Season 1", "episodeCount": 6},
        {"seasonNumber": 2, "name": "Season 2", "episodeCount": 8},
    ],
    "mediaInfo": {"status": 4, "seasons": [{"seasonNumber": 1, "status": 5}]},
}


async def test_version(hass: HomeAssistant, entry, hass_ws_client) -> None:
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/version"})
    msg = await ws.receive_json()
    assert msg["result"] == {"version": CARD_VERSION}


async def test_search(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/search", json=SEARCH)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/search", "query": "dune", "media_type": "movie"})
    msg = await ws.receive_json()
    assert msg["success"]
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [438631]


async def test_seasons(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/90228", json=TV)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/seasons", "tmdb_id": 90228})
    msg = await ws.receive_json()
    assert msg["result"]["seasons"] == [
        {"season_number": 1, "name": "Season 1", "episode_count": 6, "status": "available"},
        {"season_number": 2, "name": "Season 2", "episode_count": 8, "status": "not_requested"},
    ]


async def test_request(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.post(f"{API}/request", json={"id": 9}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/request", "tmdb_id": 90228, "media_type": "tv", "seasons": [2]}
    )
    msg = await ws.receive_json()
    assert msg["result"]["request_id"] == 9
    assert aioclient_mock.mock_calls[-1][2]["seasons"] == [2]


async def test_error_reaches_card(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.post(f"{API}/request", json={"message": "Quota exceeded"}, status=403)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/request", "tmdb_id": 1, "media_type": "movie"})
    msg = await ws.receive_json()
    assert not msg["success"]
