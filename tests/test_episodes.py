"""Episode picker: Sonarr directly, for single episodes and following new ones."""

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.jellyseerr_search.episodes import (
    async_search_followed,
    async_sweep_added,
    due_followed_episodes,
)

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
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/release?episodeId=102", json=[{"title": "Show.S02E02", "episodeIds": None, "mappedEpisodeInfo": [{"id": 102}]}])
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102, 105]})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert calls(aioclient_mock, "put", "/episode/monitor")[0][2] == {"episodeIds": [102, 105], "monitored": True}
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [102, 105]}
    # Only the aired episode is probed, and it matched: the type is left alone.
    assert not calls(aioclient_mock, "put", "/series/5")
    assert msg["result"]["series_type_changed"] is None
    # Confirmed, so the next download skips the test search.
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [104]})
    assert (await ws.receive_json())["success"]
    assert len(calls(aioclient_mock, "get", "/release")) == 1


async def test_download_keeps_the_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    picker.runtime_data.added_shows.add(5)
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/release?episodeId=102", json=[{"episodeIds": None, "mappedEpisodeInfo": [{"id": 102}]}])
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102]})
    assert (await ws.receive_json())["success"]
    assert picker.runtime_data.added_shows.due(dt_util.utcnow() + timedelta(days=1)) == []


async def test_download_finds_a_daily_show_by_itself(hass, picker, aioclient_mock, hass_ws_client) -> None:
    """Standard search finds nothing, Daily does: the show becomes Daily."""
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(
        f"{SONARR}/release?episodeId=102",
        side_effect=_sequence(
            [],
            [
                {"title": "Show.2000.01.01", "episodeIds": None, "mappedEpisodeInfo": [{"id": 102}]},
                {"episodeIds": None, "mappedEpisodeInfo": [{"id": 999}]},
            ],
        ),
    )
    aioclient_mock.put(f"{SONARR}/series/5", json={**SERIES, "seriesType": "daily"})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102, 104]})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["series_type_changed"] == "daily" and msg["result"]["daily"] is True
    puts = calls(aioclient_mock, "put", "/series/5")
    assert [p[2]["seriesType"] for p in puts] == ["daily"]
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [102, 104]}


async def test_download_puts_the_type_back_if_nothing_matches(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(102, 2)])
    aioclient_mock.get(f"{SONARR}/release?episodeId=102", json=[{"title": "Other.Show.S01E01", "episodeIds": None, "mappedEpisodeInfo": [{"id": 7}]}])
    aioclient_mock.put(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102]})
    msg = await ws.receive_json()
    assert msg["result"]["series_type_changed"] is None
    assert [p[2]["seriesType"] for p in calls(aioclient_mock, "put", "/series/5")] == ["daily", "standard"]


async def test_download_of_unaired_episodes_checks_an_aired_one(hass, picker, aioclient_mock, hass_ws_client) -> None:
    """Only a future episode picked: the show's latest aired episode is tested instead."""
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/release?episodeId=101", json=[{"mappedEpisodeInfo": [{"id": 101}]}])
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [105]})
    assert (await ws.receive_json())["success"]
    assert [c[1].query["episodeId"] for c in calls(aioclient_mock, "get", "/release")] == ["101"]


async def test_specials_are_not_used_for_the_check(hass, picker, aioclient_mock, hass_ws_client) -> None:
    """Following tests a regular episode, not a newer special (rarely on indexers)."""
    following = {**SERIES, "monitorNewItems": "all", "seasons": [*SERIES["seasons"][:2], {"seasonNumber": 2, "monitored": True}]}
    eps = [
        {**ep(101, 1), "seasonNumber": 2, "airDateUtc": _at(24 * 30)},
        {**ep(900, 54), "seasonNumber": 0, "airDateUtc": _at(24)},
    ]
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5&seasonNumber=2", json=eps[:1])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=eps)
    aioclient_mock.get(f"{SONARR}/release?episodeId=101", json=[{"mappedEpisodeInfo": [{"id": 101}]}])
    aioclient_mock.put(f"{SONARR}/series/5", json=following)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/options", "series_id": 5, "follow_new": True})
    assert (await ws.receive_json())["success"]
    assert [c[1].query["episodeId"] for c in calls(aioclient_mock, "get", "/release")] == ["101"]


async def test_nothing_aired_skips_the_check(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(105, 5, aired=False)])
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [105]})
    assert (await ws.receive_json())["success"]
    assert not calls(aioclient_mock, "get", "/release")


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
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/release?episodeId=101", json=[{"mappedEpisodeInfo": [{"id": 101}]}])
    aioclient_mock.put(f"{SONARR}/series/5", json=followed)
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/options", "series_id": 5, "follow_new": True})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["follow_new"] is True
    assert 5 in picker.runtime_data.followed.shows()
    # Naming checked before following (it matched, so the type wasn't touched).
    assert msg["result"]["series_type_changed"] is None
    assert calls(aioclient_mock, "get", "/release")
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
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=SEASON_2)
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/options", "series_id": 5, "daily": True})
    msg = await ws.receive_json()
    assert msg["result"]["daily"] is True
    put = calls(aioclient_mock, "put", "/series/5")[0][2]
    assert put["seriesType"] == "daily" and put["seasons"] == SERIES["seasons"]
    # Wanted episodes searched again by date: aired, monitored, no file (103 only;
    # 101 has its file, 105 hasn't aired).
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [103]}


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


async def test_remove_episode_deletes_file_and_unmonitors(hass, picker, aioclient_mock, hass_ws_client) -> None:
    before = [
        {**ep(101, 1, has_file=True, monitored=True), "episodeFileId": 900},
        {**ep(103, 3, has_file=True, monitored=True), "episodeFileId": 901},
    ]
    after = [{**before[0], "hasFile": False, "monitored": False, "episodeFileId": 0}, before[1]]
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", side_effect=_sequence(before, after))
    aioclient_mock.delete(f"{SONARR}/episodefile/bulk", json={})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.get(f"{SONARR}/series/5", json={**SERIES, "statistics": {"episodeFileCount": 1}})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/remove", "series_id": 5, "episode_ids": [101]})
    msg = await ws.receive_json()
    assert msg["result"] == {"series_id": 5, "files_removed": 1, "show_removed": False}
    assert calls(aioclient_mock, "delete", "/episodefile/bulk")[0][2] == {"episodeFileIds": [900]}
    assert calls(aioclient_mock, "put", "/episode/monitor")[0][2] == {"episodeIds": [101], "monitored": False}
    assert not calls(aioclient_mock, "delete", "/series/5")


async def test_removing_the_last_episode_removes_the_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    before = [{**ep(101, 1, has_file=True, monitored=True), "episodeFileId": 900}]
    after = [{**before[0], "hasFile": False, "monitored": False, "episodeFileId": 0}]
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", side_effect=_sequence(before, after))
    aioclient_mock.delete(f"{SONARR}/episodefile/bulk", json={})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.delete(f"{SONARR}/series/5", status=200)
    aioclient_mock.get(f"{API}/tv/291431", json={"id": 291431, "mediaInfo": {"id": 12, "status": 4}})
    aioclient_mock.delete(f"{API}/media/12", status=204)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/episodes/remove", "series_id": 5, "tmdb_id": 291431, "episode_ids": [101]}
    )
    msg = await ws.receive_json()
    assert msg["result"]["show_removed"] is True
    assert calls(aioclient_mock, "delete", "/series/5")
    # Jellyseerr forgets it now, not at its nightly availability sync.
    assert any(c[0].lower() == "delete" and c[1].path == "/api/v1/media/12" for c in aioclient_mock.mock_calls)


async def test_remove_all_falls_back_to_sonarr(hass, picker, aioclient_mock, hass_ws_client) -> None:
    """A picker download Jellyseerr hasn't scanned yet: removed straight from Sonarr."""
    aioclient_mock.get(f"{API}/tv/21502", json={"id": 21502, "mediaInfo": None, "externalIds": {"tvdbId": 252963}})
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[SERIES])
    aioclient_mock.delete(f"{SONARR}/series/5", status=200)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/remove", "tmdb_id": 21502, "media_type": "tv"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    delete = calls(aioclient_mock, "delete", "/series/5")[0]
    assert dict(delete[1].query) == {"deleteFiles": "true", "addImportListExclusion": "false"}


async def test_remove_all_prefers_jellyseerr(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/21502", json={"id": 21502, "mediaInfo": {"id": 11}, "externalIds": {"tvdbId": 252963}})
    aioclient_mock.delete(f"{API}/media/11/file", status=204)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/remove", "tmdb_id": 21502, "media_type": "tv"})
    assert (await ws.receive_json())["success"]
    assert not calls(aioclient_mock, "delete", "/series/5")


async def test_remove_all_when_nobody_has_it(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/21502", json={"id": 21502, "mediaInfo": None, "externalIds": {"tvdbId": 252963}})
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/remove", "tmdb_id": 21502, "media_type": "tv"})
    msg = await ws.receive_json()
    assert msg["error"]["translation_key"] == "not_in_library"


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


def _sequence_status(body, status):
    """side_effect: first call answers `body` with 200, later calls fail with `status`."""
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

    calls_made = []

    async def respond(method, url, data):
        calls_made.append(1)
        if len(calls_made) == 1:
            return AiohttpClientMockResponse(method, url, json=body)
        return AiohttpClientMockResponse(method, url, status=status, json={"message": "Indexer error"})

    return respond


def _sequence(*bodies):
    """side_effect answering with each body in turn, then the last one again."""
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

    remaining = list(bodies)

    async def respond(method, url, data):
        body = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return AiohttpClientMockResponse(method, url, json=body)

    return respond


def _at(hours_ago: float) -> str:
    return (dt_util.utcnow() - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_due_followed_episodes() -> None:
    now = dt_util.utcnow()
    since = now - timedelta(days=60)
    iso = lambda h: (now - timedelta(hours=h)).isoformat()
    eps = [
        {"id": 1, "seasonNumber": 1, "airDateUtc": _at(24 * 70), "hasFile": False, "monitored": False},  # before following
        {"id": 2, "seasonNumber": 1, "airDateUtc": _at(24 * 30), "hasFile": False, "monitored": False},  # listed late: due
        {"id": 3, "seasonNumber": 1, "airDateUtc": _at(1), "hasFile": False, "monitored": False},        # too fresh
        {"id": 4, "seasonNumber": 1, "airDateUtc": _at(30), "hasFile": True, "monitored": True},         # on disk
        {"id": 5, "seasonNumber": 1, "airDateUtc": _at(30), "hasFile": False, "monitored": False},       # downloading
        {"id": 6, "seasonNumber": 1, "airDateUtc": _at(40), "hasFile": False, "monitored": True},        # Sonarr's own job
        {"id": 7, "seasonNumber": 1, "airDateUtc": _at(50), "hasFile": False, "monitored": False},       # removed by the user
        {"id": 8, "seasonNumber": 0, "airDateUtc": _at(50), "hasFile": False, "monitored": False},       # special
        {"id": 9, "seasonNumber": 1, "airDateUtc": None, "hasFile": False, "monitored": False},          # no air date
        {"id": 10, "seasonNumber": 1, "airDateUtc": _at(24 * 40), "hasFile": False, "monitored": True},  # retry due
        {"id": 11, "seasonNumber": 1, "airDateUtc": _at(24 * 40), "hasFile": False, "monitored": True},  # retried 2 h ago
        {"id": 12, "seasonNumber": 1, "airDateUtc": _at(24 * 40), "hasFile": False, "monitored": True},  # gave up
    ]
    searched = {
        "10": {"first": iso(24 * 3), "last": iso(7)},
        "11": {"first": iso(24 * 3), "last": iso(2)},
        "12": {"first": iso(24 * 15), "last": iso(7)},
    }
    due = due_followed_episodes(eps, since, searched, {7}, {5}, now)
    assert [e["id"] for e in due] == [2, 10]


async def test_followed_shows_get_late_episodes_searched(hass, picker, aioclient_mock) -> None:
    followed = picker.runtime_data.followed
    followed.follow(5)
    followed._shows["5"]["since"] = (dt_util.utcnow() - timedelta(days=40)).isoformat()
    following = {**SERIES, "monitorNewItems": "all", "seasons": [*SERIES["seasons"][:2], {"seasonNumber": 2, "monitored": True}]}
    aioclient_mock.get(f"{SONARR}/series/5", json=following)
    aioclient_mock.get(
        f"{SONARR}/episode?seriesId=5",
        json=[
            # Listed a month late, so Sonarr unmonitored it: ours.
            {"id": 201, "seasonNumber": 2, "airDateUtc": _at(24 * 30), "hasFile": False, "monitored": False},
            # Monitored: Sonarr's RSS and its own refresh search cover it.
            {"id": 202, "seasonNumber": 2, "airDateUtc": _at(10), "hasFile": False, "monitored": True},
        ],
    )
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)

    await async_search_followed(picker.runtime_data.sonarr, followed)
    assert calls(aioclient_mock, "put", "/episode/monitor")[0][2] == {"episodeIds": [201], "monitored": True}
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [201]}

    # Not again within 6 hours.
    await async_search_followed(picker.runtime_data.sonarr, followed)
    assert len(calls(aioclient_mock, "post", "/command")) == 1


async def test_removed_episode_of_a_followed_show_stays_removed(hass, picker, aioclient_mock, hass_ws_client) -> None:
    followed = picker.runtime_data.followed
    followed.follow(5)
    before = [{**ep(101, 1, has_file=True, monitored=True), "episodeFileId": 900}, ep(103, 3, monitored=True)]
    after = [{**before[0], "hasFile": False, "monitored": False, "episodeFileId": 0}, before[1]]
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", side_effect=_sequence(before, after))
    aioclient_mock.delete(f"{SONARR}/episodefile/bulk", json={})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/remove", "series_id": 5, "episode_ids": [101]})
    assert (await ws.receive_json())["success"]
    assert followed.shows()[5]["removed"] == [101]


async def test_type_is_put_back_if_the_second_search_fails(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", json=[ep(102, 2)])
    aioclient_mock.get(f"{SONARR}/release?episodeId=102", side_effect=_sequence_status([], 500))
    aioclient_mock.put(f"{SONARR}/series/5", json=SERIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102]})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert [p[2]["seriesType"] for p in calls(aioclient_mock, "put", "/series/5")] == ["daily", "standard"]


async def test_download_on_a_show_gone_from_sonarr(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{SONARR}/series/5", json={"message": "NotFound"}, status=404)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/download", "series_id": 5, "episode_ids": [102]})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert msg["error"]["translation_key"] == "series_gone"


async def test_listing_keeps_a_picker_added_show_alive(hass, picker, aioclient_mock, hass_ws_client) -> None:
    added = picker.runtime_data.added_shows
    added.add(5)
    added._added["5"] = (dt_util.utcnow() - timedelta(minutes=50)).isoformat()
    aioclient_mock.get(f"{API}/tv/21502", json={"externalIds": {"tvdbId": 252963}})
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[SERIES])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5&seasonNumber=2", json=SEASON_2)
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes", "tmdb_id": 21502, "season_number": 2})
    assert (await ws.receive_json())["success"]
    # 70 min after adding but 20 after looking: not due yet.
    assert added.due(dt_util.utcnow() + timedelta(minutes=20)) == []


async def test_a_requested_show_keeps_its_seerr_history(hass, picker, aioclient_mock, hass_ws_client) -> None:
    before = [{**ep(101, 1, has_file=True, monitored=True), "episodeFileId": 900}]
    after = [{**before[0], "hasFile": False, "monitored": False, "episodeFileId": 0}]
    aioclient_mock.get(f"{SONARR}/episode?seriesId=5", side_effect=_sequence(before, after))
    aioclient_mock.delete(f"{SONARR}/episodefile/bulk", json={})
    aioclient_mock.put(f"{SONARR}/episode/monitor", json=[])
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)
    aioclient_mock.delete(f"{SONARR}/series/5", status=200)
    aioclient_mock.get(f"{API}/tv/82684", json={"id": 82684, "mediaInfo": {"id": 5, "status": 4, "requests": [{"id": 1}]}})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/remove", "series_id": 5, "tmdb_id": 82684, "episode_ids": [101]})
    assert (await ws.receive_json())["result"]["show_removed"] is True
    assert not any(c[0].lower() == "delete" and c[1].path.startswith("/api/v1/media") for c in aioclient_mock.mock_calls)


async def test_unfollowed_when_off_or_gone(hass, picker, aioclient_mock) -> None:
    followed = picker.runtime_data.followed
    followed.follow(5)
    followed.follow(6)
    aioclient_mock.get(f"{SONARR}/series/5", json=SERIES)  # not following any more
    aioclient_mock.get(f"{SONARR}/series/6", status=404)
    await async_search_followed(picker.runtime_data.sonarr, followed)
    assert followed.shows() == {}
