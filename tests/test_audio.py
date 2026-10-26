"""Anime audio: dub or sub per title, what the files have, and dub dates."""

from datetime import datetime, timezone

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.jellyseerr_search.animeschedule import AnimeScheduleClient, DubSchedule, names_match
from custom_components.jellyseerr_search.audio import file_audio, is_anime, show_audio
from custom_components.jellyseerr_search.const import DOMAIN

from .common import API, COUNTS
from .test_episodes import (
    RADARR,
    SERIES,
    SONARR,
    _movie,
    _no_sleep,
    arrs,  # noqa: F401 (fixture)
    calls,
    ep,
    first,
    picker,  # noqa: F401 (fixture)
)

PROFILES = [
    {"id": 7, "name": "WEB-1080p"},
    {"id": 8, "name": "Anime (English dub preferred)"},
    {"id": 9, "name": "Anime (English dub only)"},
    {"id": 10, "name": "Anime (Japanese + subtitles)"},
]
ANIME = {"externalIds": {"tvdbId": 431162}, "name": "The Apothecary Diaries", "originalName": "薬屋のひとりごと",
         "keywords": [{"id": 210024, "name": "anime"}], "genres": [{"id": 16, "name": "Animation"}],
         "originalLanguage": "ja"}
APOTHECARY = {**SERIES, "id": 16, "title": "The Apothecary Diaries", "tvdbId": 431162, "qualityProfileId": 9,
              "alternateTitles": [{"title": "Kusuriya no Hitorigoto"}], "images": [],
              "statistics": {"episodeFileCount": 3}}


def jpn(file_id, season=3):
    return {"id": file_id, "seasonNumber": season, "mediaInfo": {"audioLanguages": "jpn", "subtitles": "eng/ger"}}


def dual(file_id, season=3):
    return {"id": file_id, "seasonNumber": season, "mediaInfo": {"audioLanguages": "eng/jpn", "subtitles": "eng"}}


def with_file(ep_, file_id):
    return {**ep_, "hasFile": True, "episodeFileId": file_id}


S3 = [
    with_file(ep(301, 1, season=3, monitored=True), 1),  # dub
    with_file(ep(302, 2, season=3, monitored=True), 2),  # Japanese
    with_file(ep(303, 3, season=3, monitored=True), 3),  # Japanese
    ep(304, 4, season=3, monitored=True),  # aired, missing
    ep(305, 5, season=3, monitored=True, aired=False),
]
S3_FILES = [dual(1), jpn(2), jpn(3)]


@pytest.mark.parametrize(
    ("audio", "expected"),
    [("eng/jpn", "dual"), ("eng", "dub"), ("jpn", "sub"), ("jpn/und", "sub"), ("", None), ("und", None), (None, None)],
)
def test_file_audio(audio, expected) -> None:
    assert file_audio({"audioLanguages": audio}) == expected


def test_show_audio() -> None:
    assert show_audio([dual(1), dual(2)]) == "dub"
    assert show_audio([dual(1), jpn(2)]) == "part_dub"
    assert show_audio([jpn(1), {**jpn(2), "seasonNumber": 0}]) == "sub_only"
    assert show_audio([{**dual(1), "seasonNumber": 0}]) is None  # specials don't count
    assert show_audio([]) is None


def test_is_anime() -> None:
    assert is_anime(ANIME)
    # Seerr's keyword misses some (Slime): Japanese animation counts too.
    assert is_anime({"originalLanguage": "ja", "genres": [{"id": 16}]})
    assert not is_anime({"originalLanguage": "en", "genres": [{"id": 16}]})
    assert not is_anime({"originalLanguage": "ja", "genres": [{"id": 18}]})


def test_names_match() -> None:
    names = ["The Apothecary Diaries", "Kusuriya no Hitorigoto"]
    assert names_match({"english": "The Apothecary Diaries Season 3"}, names)
    assert names_match({"romaji": "Kusuriya no Hitorigoto 3rd Season"}, names)
    assert names_match({"title": "the apothecary diaries!"}, names)
    assert not names_match({"english": "The Apothecary Diaries: Maomao's Movie Night"}, names)
    assert not names_match({"english": "Slime"}, ["Slime"])  # too short to trust


async def test_anime_added_by_the_picker_goes_to_seerrs_anime_profile(hass, picker, aioclient_mock, hass_ws_client, monkeypatch) -> None:
    monkeypatch.setattr("custom_components.jellyseerr_search.episodes.asyncio.sleep", _no_sleep)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{API}/settings/sonarr", json=[
        {"is4k": False, "isDefault": True, "activeProfileId": 7, "activeDirectory": "/data/media/tv",
         "activeAnimeProfileId": 8, "activeAnimeDirectory": "/data/media/anime"},
    ])
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[])
    aioclient_mock.get(f"{SONARR}/series/lookup?term=tvdb:431162", json=[{**APOTHECARY, "id": None}])
    aioclient_mock.post(f"{SONARR}/series", json=APOTHECARY, status=201)
    aioclient_mock.get(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16&seasonNumber=3", json=S3)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes", "tmdb_id": 220542, "season_number": 3})
    msg = await ws.receive_json()
    assert msg["success"], msg
    body = calls(aioclient_mock, "post", "/series")[0][2]
    assert body["qualityProfileId"] == 8 and body["rootFolderPath"] == "/data/media/anime"
    assert [(e["episode_number"], e["audio"], e["english_subs"]) for e in msg["result"]["episodes"]] == [
        (1, "dual", True), (2, "sub", True), (3, "sub", True), (4, None, False), (5, None, False),
    ]


async def test_the_audio_chosen_picks_the_profile(hass, picker, aioclient_mock, hass_ws_client, monkeypatch) -> None:
    monkeypatch.setattr("custom_components.jellyseerr_search.episodes.asyncio.sleep", _no_sleep)
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{API}/settings/sonarr", json=[
        {"is4k": False, "isDefault": True, "activeProfileId": 7, "activeDirectory": "/data/media/tv", "activeAnimeProfileId": 8},
    ])
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[])
    aioclient_mock.get(f"{SONARR}/series/lookup?term=tvdb:431162", json=[{**APOTHECARY, "id": None}])
    aioclient_mock.post(f"{SONARR}/series", json=APOTHECARY, status=201)
    aioclient_mock.get(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    aioclient_mock.put(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    aioclient_mock.get(f"{SONARR}/release?episodeId=301", json=[{"title": "x", "mappedEpisodeInfo": [{"id": 301}]}])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/request", "tmdb_id": 220542, "seasons": [3], "audio": "dub_only"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert calls(aioclient_mock, "post", "/series")[0][2]["qualityProfileId"] == 9


async def test_audio_choice_needs_the_profiles(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[])
    aioclient_mock.get(f"{SONARR}/series/lookup?term=tvdb:431162", json=[{**APOTHECARY, "id": None}])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/episodes/follow", "tmdb_id": 220542, "follow_new": True, "audio": "sub"})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert msg["error"]["translation_key"] == "no_audio_profile"


async def test_audio_state_of_a_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[APOTHECARY])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 220542, "media_type": "tv"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"] == {
        "available": True, "anime": True, "audio": "dub_only", "in_arr": True,
        "files": 3, "english_files": 1, "summary": "part_dub", "dub_wanted": 2, "dub": None, "dub_dates": False,
    }


async def test_audio_state_of_an_ordinary_show(hass, picker, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/21502", json={"externalIds": {"tvdbId": 252963}, "originalLanguage": "en"})
    aioclient_mock.get(f"{SONARR}/series?tvdbId=252963", json=[SERIES])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 21502, "media_type": "tv"})
    result = (await ws.receive_json())["result"]
    assert result["anime"] is False and result["available"] is False and result["audio"] is None


async def test_changing_to_a_dub_searches_episodes_not_in_english(hass, picker, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    on_sub = {**APOTHECARY, "qualityProfileId": 10}
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[on_sub])
    aioclient_mock.get(f"{SONARR}/series/16", json=on_sub)
    aioclient_mock.put(f"{SONARR}/series/16", json={**on_sub, "qualityProfileId": 8})
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    aioclient_mock.post(f"{SONARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 220542, "media_type": "tv", "audio": "dub"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    put = calls(aioclient_mock, "put", "/series/16")[0][2]
    assert put == {**on_sub, "qualityProfileId": 8}  # only the profile changed
    # E02, E03 are Japanese, E04 is missing; E01 is dubbed, E05 not aired.
    assert calls(aioclient_mock, "post", "/command")[0][2] == {"name": "EpisodeSearch", "episodeIds": [302, 303, 304]}


async def test_changing_to_sub_searches_nothing(hass, picker, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[APOTHECARY])
    aioclient_mock.get(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.put(f"{SONARR}/series/16", json={**APOTHECARY, "qualityProfileId": 10})
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 220542, "media_type": "tv", "audio": "sub"})
    assert (await ws.receive_json())["success"]
    assert calls(aioclient_mock, "post", "/command") == []


async def test_audio_of_a_title_not_in_sonarr_yet(hass, picker, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 220542, "media_type": "tv", "audio": "dub"})
    msg = await ws.receive_json()
    assert msg["error"]["translation_key"] == "not_in_arr"


async def test_anime_film_request_carries_the_dub_profile(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{RADARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{API}/movie/1311034", json={"keywords": [{"id": 210024}]})
    aioclient_mock.get(f"{API}/movie/438631", json={"keywords": [], "originalLanguage": "en"})
    aioclient_mock.post(f"{API}/request", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/request", "tmdb_id": 1311034, "media_type": "movie"})
    assert (await ws.receive_json())["success"]
    await ws.send_json_auto_id({"type": f"{DOMAIN}/request", "tmdb_id": 1311034, "media_type": "movie", "audio": "sub"})
    assert (await ws.receive_json())["success"]
    await ws.send_json_auto_id({"type": f"{DOMAIN}/request", "tmdb_id": 438631, "media_type": "movie"})
    assert (await ws.receive_json())["success"]
    bodies = [c[2] for c in aioclient_mock.mock_calls if c[0].lower() == "post" and c[1].path == "/api/v1/request"]
    assert [b.get("profileId") for b in bodies] == [8, 10, None]


async def test_film_audio_change_uses_radarrs_editor(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{RADARR}/qualityprofile", json=PROFILES)
    film = {**_movie(8, "Infinity Castle 2", "released", has_file=True), "tmdbId": 1311034, "qualityProfileId": 10,
            "movieFile": {"mediaInfo": {"audioLanguages": "jpn"}}}
    aioclient_mock.get(f"{API}/movie/1311034", json={"keywords": [{"id": 210024}]})
    aioclient_mock.get(f"{RADARR}/movie?tmdbId=1311034", json=[film])
    aioclient_mock.put(f"{RADARR}/movie/editor", json=[film])
    aioclient_mock.post(f"{RADARR}/command", json={"id": 1}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 1311034, "media_type": "movie", "audio": "dub"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert calls_radarr(aioclient_mock, "put", "/movie/editor")[0][2] == {"movieIds": [8], "qualityProfileId": 8}
    assert calls_radarr(aioclient_mock, "post", "/command")[0][2] == {"name": "MoviesSearch", "movieIds": [8]}
    assert msg["result"]["summary"] == "sub_only"


def calls_radarr(aioclient_mock, method, path):
    return [c for c in aioclient_mock.mock_calls if c[0].lower() == method and c[1].host == "radarr.local" and c[1].path == f"/api/v3{path}"]


async def test_waiting_lists_shows_waiting_for_their_dub(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{RADARR}/movie", json=[])
    aioclient_mock.get(f"{RADARR}/queue", json={"records": []})
    all_here = [with_file(ep(301, 1, season=3, monitored=True), 1), with_file(ep(302, 2, season=3, monitored=True), 2)]
    aioclient_mock.get(f"{SONARR}/series", json=[{**APOTHECARY, "tmdbId": 220542, "qualityProfileId": 8}])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=all_here)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=[dual(1), jpn(2)])
    aioclient_mock.get(f"{SONARR}/wanted/missing", json={"records": []})
    aioclient_mock.get(f"{SONARR}/calendar", json=[])
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/waiting"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    [item] = msg["result"]["results"]
    assert (item["state"], item["audio"], item["dub_wanted"], item["next_dub"]) == ("dub_wanted", "dub", 1, None)


async def test_check_now_on_a_dub_wait_checks_a_japanese_episode(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3[:3])
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.get(f"{SONARR}/release?episodeId=302", json=[
        {"title": "Show.S03E02.DUAL", "approved": True, "rejections": [], "mappedEpisodeInfo": [{"id": 302}],
         "customFormats": [{"name": "Anime Dual Audio"}]},
        {"title": "Show.S03E02.JPN", "approved": False, "rejections": ["below minimum"], "mappedEpisodeInfo": [{"id": 302}],
         "customFormats": [{"name": "CR"}]},
    ])
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/waiting/check", "media_type": "tv", "arr_id": 16})
    result = (await ws.receive_json())["result"]
    assert result["episode"] == {"season": 3, "episode": 2}
    assert (result["found"], result["accepted"], result["dubbed"]) == (2, 1, 1)


async def test_search_again_includes_episodes_waiting_for_a_dub(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{SONARR}/series/16", json=APOTHECARY)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.post(f"{SONARR}/command", json={"id": 2}, status=201)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/waiting/search", "media_type": "tv", "arr_id": 16})
    assert (await ws.receive_json())["success"]
    assert [c[2] for c in aioclient_mock.mock_calls if c[0].lower() == "post" and "/command" in c[1].path] == [
        {"name": "MissingEpisodeSearch", "seriesId": 16},
        {"name": "EpisodeSearch", "episodeIds": [302, 303]},
    ]


async def test_result_chips_say_dub_or_sub(hass, arrs, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    first(aioclient_mock, "get", f"{RADARR}/qualityprofile", json=PROFILES)
    aioclient_mock.get(f"{API}/search", json={"results": [
        {"id": 220542, "mediaType": "tv", "name": "The Apothecary Diaries"},
        {"id": 1311034, "mediaType": "movie", "title": "Infinity Castle"},
    ]})
    aioclient_mock.get(f"{RADARR}/movie", json=[{**_movie(8, "Infinity Castle", "released", has_file=True), "tmdbId": 1311034,
                                               "qualityProfileId": 8, "movieFile": {"mediaInfo": {"audioLanguages": "eng/jpn"}}}])
    aioclient_mock.get(f"{RADARR}/queue", json={"records": []})
    aioclient_mock.get(f"{SONARR}/series", json=[{**APOTHECARY, "tmdbId": 220542}])
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    aioclient_mock.get(f"{SONARR}/wanted/missing", json={"records": []})
    aioclient_mock.get(f"{SONARR}/calendar", json=[])
    aioclient_mock.get(f"{SONARR}/queue", json={"records": []})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/search", "query": "x"})
    results = (await ws.receive_json())["result"]["results"]
    assert [r["arr"].get("audio") for r in results] == ["part_dub", "dub"]


TIMETABLE = [
    {"title": "The Apothecary Diaries Season 3", "english": "The Apothecary Diaries Season 3",
     "romaji": "Kusuriya no Hitorigoto 3rd Season", "route": "kusuriya-3", "episodeNumber": 2,
     "episodeDate": "2026-10-23T15:00:00Z", "airingStatus": "aired", "episodes": 12},
    {"title": "The Apothecary Diaries Season 3", "english": "The Apothecary Diaries Season 3",
     "romaji": "Kusuriya no Hitorigoto 3rd Season", "route": "kusuriya-3", "episodeNumber": 3,
     "episodeDate": "2026-10-30T15:00:00Z", "airingStatus": "unaired", "episodes": 12},
    {"title": "Another Show", "route": "another", "episodeNumber": 9, "episodeDate": "2026-10-28T12:00:00Z"},
]


class FakeClient:
    def __init__(self) -> None:
        self.weeks: list[tuple[int, int]] = []

    async def async_dub_week(self, year, week):
        self.weeks.append((year, week))
        return TIMETABLE if not self.weeks[:-1] else []


async def test_next_dub_from_the_timetable() -> None:
    client = FakeClient()
    schedule = DubSchedule(client)
    now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    dub = await schedule.async_next_dub(["The Apothecary Diaries", "Kusuriya no Hitorigoto"], now)
    assert dub == {
        "episode": 3, "date_utc": "2026-10-30T15:00:00+00:00", "delayed": False, "last_episode": 2, "total": 12,
        "source": "AnimeSchedule.net", "url": "https://animeschedule.net/anime/kusuriya-3",
    }
    assert client.weeks == [(2026, 44), (2026, 45), (2026, 46), (2026, 47)]
    assert await schedule.async_next_dub(["Slime"], now) is None
    assert len(client.weeks) == 4  # cached


async def test_dub_dates_in_the_audio_state(hass, picker, aioclient_mock, hass_ws_client) -> None:
    first(aioclient_mock, "get", f"{SONARR}/qualityprofile", json=PROFILES)
    first(aioclient_mock, "get", f"{SONARR}/episodefile?seriesId=16", json=S3_FILES)
    aioclient_mock.get(f"{API}/tv/220542", json=ANIME)
    aioclient_mock.get(f"{SONARR}/series?tvdbId=431162", json=[APOTHECARY])
    aioclient_mock.get(f"{SONARR}/episode?seriesId=16", json=S3)
    aioclient_mock.get("https://animeschedule.net/api/v3/timetables/dub", json=[
        {**TIMETABLE[1], "episodeDate": "2999-10-30T15:00:00Z"},
    ])
    picker.runtime_data.schedule = DubSchedule(AnimeScheduleClient(async_get_clientsession(hass), "token"))
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/audio", "tmdb_id": 220542, "media_type": "tv"})
    result = (await ws.receive_json())["result"]
    assert result["dub"]["episode"] == 3 and result["dub"]["date_utc"].startswith("2999-10-30")
    request = next(c for c in aioclient_mock.mock_calls if c[1].host == "animeschedule.net")
    assert request[3]["Authorization"] == "Bearer token"


async def test_options_flow_checks_the_token(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get("https://animeschedule.net/api/v3/timetables/dub", status=401)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"animeschedule_token": "bad"})
    assert result["errors"] == {"base": "animeschedule_failed"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{API}/request/count", json=COUNTS)  # the entry reloads
    aioclient_mock.get("https://animeschedule.net/api/v3/timetables/dub", json=[])
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"animeschedule_token": "good"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"animeschedule_token": "good"}
    await hass.async_block_till_done()
    assert entry.runtime_data.schedule is not None
