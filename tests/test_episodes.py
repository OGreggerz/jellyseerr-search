"""Episode picker: Sonarr directly, for single episodes and following new ones."""

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.jellyseerr_search.episodes import async_sweep_added

from custom_components.jellyseerr_search.const import DOMAIN

from .common import API, COUNTS, DATA, URL

SONARR_URL = "http://sonarr.local:8989"
SONARR = f"{SONARR_URL}/api/v3"
OPTIONS = {"sonarr_url": SONARR_URL, "sonarr_api_key": "sonarr-secret"}

AIRED = "2000-01-01T19:00:00Z"
FUTURE = "2999-01-01T19:00:00Z"

SERIES = {
    "id": 5,
    "title": "The Chase",
    "tvdbId": 252963,
    "seriesType": "standard",
    "monitored": True,
    "monitorNewItems": "none",
    "seasons": [
        {"seasonNumber": 0, "monitored": False},
        {"seasonNumber": 1, "monitored": False},
        {"seasonNumber": 2, "monitored": False},
    ],
    "statistics": {"episodeFileCount": 0},
}


def ep(id_: int, number: int, *, aired=True, monitored=False, has_file=False, season=2):
    return {
        "id": id_,
        "seasonNumber": season,
        "episodeNumber": number,
        "title": f"Episode {number}",
        "airDate": "2000-01-01" if aired else "2999-01-01",
        "airDateUtc": AIRED if aired else FUTURE,
        "monitored": monitored,
        "hasFile": has_file,
    }


SEASON_2 = [
    ep(101, 1, has_file=True, monitored=True),
    ep(102, 2),
    ep(103, 3, monitored=True),
    ep(104, 4),
    ep(105, 5, aired=False),
]


@pytest.fixture
async def picker(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(f"{API}/request/count", json=COUNTS)
    entry = MockConfigEntry(domain=DOMAIN, title="Jellyseerr", data=DATA, unique_id=URL, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def calls(aioclient_mock, method: str, path: str):
    return [c for c in aioclient_mock.mock_calls if c[0].lower() == method and c[1].path == f"/api/v3{path}"]


async def test_seasons_say_whether_picker_is_on(hass, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/1", json={"id": 1, "seasons": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/seasons", "tmdb_id": 1})
    assert (await ws.receive_json())["result"]["episode_picker"] is False


async def test_picker_needs_sonarr(hass, entry, hass_ws_client) -> None:
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes", "tmdb_id": 1, "season_number": 1})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert msg["error"]["translation_key"] == "no_sonarr"


async def test_episodes_of_a_show_sonarr_has(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/21502", json={"externalIds": {"tvdbId": 252963}})
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[SERIES])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5&seasonNumber=2", json=list(reversed(SEASON_2)))
    aioclient_mock.get(f"{SONARR}/queue", json={"records": [{"episodeId": 104}]})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes", "tmdb_id": 21502, "season_number": 2})
    msg = await ws.receive_json()
    assert msg["success"], msg
    result = msg["result"]
    assert result["series_id"] == 5 and result["added"] is False
    assert result["daily"] is False and result["follow_new"] is False
    assert [(e["episode_number"], e["status"]) for e in result["episodes"]] == [
        (1, "downloaded"),
        (2, "missing"),
        (3, "wanted"),
        (4, "downloading"),
        (5, "not_aired"),
    ]
    assert calls(aioclient_mock, "get", "/series")[0][3]["X-Api-Key"] == "sonarr-secret"


async def test_a_new_show_is_added_unmonitored(hass, picker, aioclient_mock, hass_ws_client, monkeypatch) -> None:
    monkeypatch.setattr("custom_components.jellyseerr_search.episodes.asyncio.sleep", _no_sleep)
    lookup = {**SERIES, "id": None, "seasons": [{"seasonNumber": 1, "monitored": True}]}
    aioclient_mock.get(f"{API}/tv/21502", json={"externalIds": {"tvdbId": 252963}})
    aioclient_mock.get(
        f"{API}/settings/sonarr",
        json=[
            {"is4k": True, "isDefault": True, "activeProfileId": 9, "activeDirectory": "/4k"},
            {"is4k": False, "isDefault": True, "activeProfileId": 7, "activeDirectory": "/data/media/tv"},
        ],
    )
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[])
    aioclient_mock.get(f"{SONARR}/series/lookup?term=tvdb:252963", json=[lookup])
    aioclient_mock.post(f"{SONARR}/series", json=SERIES, status=201)
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5&seasonNumber=2", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes", "tmdb_id": 21502, "season_number": 2})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["added"] is True
    body = calls(aioclient_mock, "post", "/series")[0][2]
    assert body["qualityProfileId"] == 7 and body["rootFolderPath"] == "/data/media/tv"
    assert body["addOptions"] == {
        "monitor": "none",
        "searchForMissingEpisodes": False,
        "searchForCutoffUnmetEpisodes": False,
    }
    assert body["monitorNewItems"] == "none"
    assert all(not s["monitored"] for s in body["seasons"])
    # Remembered, so the sweep can remove it if nothing gets picked.
    later = dt_util.utcnow() + timedelta(hours=2)
    assert picker.runtime_data.added_shows.due(later) == [5]
    assert picker.runtime_data.added_shows.due(dt_util.utcnow()) == []


async def _no_sleep(_seconds) -> None:
    return None


async def test_download_monitors_and_searches(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102, 105]})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert calls(aioclient_mock, "put", "/episode/monitor")[0][2] == {"episodeIds": [102, 105], "monitored": True}
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [102, 105]}


async def test_download_keeps_the_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    picker.runtime_data.added_shows.add(5)
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102]})
    assert (await ws.receive_json())["success"]
    assert picker.runtime_data.added_shows.due(dt_util.utcnow() + timedelta(days=1)) == []


async def test_sweep_removes_untouched_shows_after_an_hour(hass, picker, aioclient_mock, freezer) -> None:
    added = picker.runtime_data.added_shows
    added.add(5)  # untouched
    added.add(6)  # something picked meanwhile
    added.add(7)  # Sonarr errors: try again next time
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(102, 2)])
    aioclient_mock.delete(f"{SONARR}/series/5", status=200)
    aioclient_mock.get(f"{SONARR}/series/6", json={**SERIES, "id": 6})
    aioclient_mock.get(f"{SONARR}/episode?seriesId=6", json=[ep(102, 2, monitored=True)])
    aioclient_mock.get(f"{SONARR}/series/7", status=500)

    await async_sweep_added(picker.runtime_data.sonarr, added)
    assert not calls(aioclient_mock, "delete", "/series/5")  # under an hour: left alone

    freezer.tick(timedelta(hours=1, minutes=1))
    await async_sweep_added(picker.runtime_data.sonarr, added)
    assert calls(aioclient_mock, "delete", "/series/5")
    assert not calls(aioclient_mock, "delete", "/series/6")
    assert added.due(dt_util.utcnow()) == [7]


async def test_follow_new_keeps_aired_episodes_as_they_were(hass, picker, aioclient_mock, hass_ws_client) -> None:
    after = [{**e, "monitored": True} for e in SEASON_2]  # Sonarr's cascade
    followed = {**SERIES, "monitorNewItems": "all", "seasons": [*SERIES["seasons"][:2], {"seasonNumber": 2, "monitored": True}]}
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5&seasonNumber=2", side_effect=_sequence(SEASON_2, after))
    aioclient_mock.put(f"{SONARR}/series/5", json=followed)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/options", "series_id": 5, "follow_new": True})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["follow_new"] is True
    put = calls(aioclient_mock, "put", "/series/5")[0][2]
    assert put["monitorNewItems"] == "all"
    assert [s["monitored"] for s in put["seasons"]] == [False, False, True]
    monitor = [c[2] for c in calls(aioclient_mock, "put", "/episode/monitor")]
    # Aired episodes that were monitored stay so; unmonitored aired ones go back off.
    assert {"episodeIds": [101, 103], "monitored": True} in monitor
    assert {"episodeIds": [102, 104], "monitored": False} in monitor


async def test_daily(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.put(f"{SONARR}/series/5", json={**SERIES, "seriesType": "daily"})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/options", "series_id": 5, "daily": True})
    msg = await ws.receive_json()
    assert msg["result"]["daily"] is True
    put = calls(aioclient_mock, "put", "/series/5")[0][2]
    assert put["seriesType"] == "daily" and put["seasons"] == SERIES["seasons"]


async def test_discard_removes_an_untouched_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(102, 2)])
    aioclient_mock.delete(f"{SONARR}/series/5", status=200)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/discard", "series_id": 5})
    msg = await ws.receive_json()
    assert msg["result"] == {"series_id": 5, "removed": True}


async def test_discard_keeps_a_show_with_picks(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(102, 2, monitored=True)])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/discard", "series_id": 5})
    msg = await ws.receive_json()
    assert msg["result"]["removed"] is False
    assert not calls(aioclient_mock, "delete", "/series/5")


async def test_discard_of_a_show_already_gone(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json={"message": "NotFound"}, status=404)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/discard", "series_id": 5})
    msg = await ws.receive_json()
    assert msg["result"] == {"series_id": 5, "removed": True}


async def test_sonarr_error_reaches_card(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json={"message": "Database is locked"}, status=500)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/discard", "series_id": 5})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert "Database is locked" in msg["error"]["message"]


async def test_options_flow(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{SONARR}/system/status", json={"version": "4.0.20"})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"sonarr_url": "sonarr.local:8989/", "sonarr_api_key": "sonarr-secret"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == OPTIONS
    await hass.async_block_till_done()
    assert entry.runtime_data.sonarr is not None


@pytest.mark.parametrize(
    ("mock", "error"),
    [({"status": 401}, "sonarr_invalid_auth"), ({"exc": aiohttp.ClientError}, "sonarr_cannot_connect")],
)
async def test_options_flow_errors(hass, entry, aioclient_mock, mock, error) -> None:
    aioclient_mock.get(f"{SONARR}/system/status", **mock)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"sonarr_url": SONARR_URL, "sonarr_api_key": "x"}
    )
    assert result["errors"] == {"base": error}


async def test_options_flow_half_filled(hass, entry) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"sonarr_url": SONARR_URL})
    assert result["errors"] == {"base": "sonarr_incomplete"}


async def test_options_flow_turns_picker_off(hass, picker) -> None:
    result = await hass.config_entries.options.async_init(picker.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"sonarr_url": "", "sonarr_api_key": ""}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert picker.options == {}
    await hass.async_block_till_done()
    assert picker.runtime_data.sonarr is None


def _sequence(*bodies):
    """side_effect answering with each body in turn, then the last one again."""
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

    remaining = list(bodies)

    async def respond(method, url, data):
        body = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return AiohttpClientMockResponse(method, url, json=body)

    return respond
