"""Setup, sensors, actions and repo consistency."""

import json
from pathlib import Path

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.jellyseerr_search.const import DOMAIN

from .common import API, COUNTS, SEARCH, mock_entry

COMPONENT = Path(__file__).parent.parent / "custom_components" / DOMAIN


async def test_sensors(hass: HomeAssistant, entry) -> None:
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.jellyseerr_pending_requests").state == "2"
    assert hass.states.get("sensor.jellyseerr_total_requests").state == "12"


async def test_auth_failure_starts_reauth(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/request/count", status=401)
    entry = mock_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(flow["context"]["source"] == "reauth" for flow in hass.config_entries.flow.async_progress())


async def test_search(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/search", json=SEARCH)
    resp = await hass.services.async_call(
        DOMAIN, "search", {"query": "dune: part two!"}, blocking=True, return_response=True
    )
    # Spaces as %20 and reserved characters escaped, as Jellyseerr requires.
    url = aioclient_mock.mock_calls[-1][1]
    assert url.raw_query_string == "query=dune%3A%20part%20two%21&page=1"
    assert resp["results"] == [
        {
            "tmdb_id": 438631,
            "media_type": "movie",
            "title": "Dune",
            "year": 2021,
            "overview": "Paul Atreides...",
            "poster_url": "https://image.tmdb.org/t/p/w342/d5NXSklXo0qyIYkgV94XAgMIckC.jpg",
            "status": "not_requested",
        },
        {
            "tmdb_id": 90228,
            "media_type": "tv",
            "title": "Dune: Prophecy",
            "year": 2024,
            "overview": "",
            "poster_url": None,
            "status": "available",
        },
    ]


async def test_search_filter_and_limit(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/search", json=SEARCH)
    resp = await hass.services.async_call(
        DOMAIN, "search", {"query": "dune", "media_type": "tv", "limit": 1},
        blocking=True, return_response=True,
    )
    assert [r["tmdb_id"] for r in resp["results"]] == [90228]


@pytest.mark.parametrize(
    ("data", "body"),
    [
        (
            {"tmdb_id": 438631, "media_type": "movie", "seasons": "1"},
            {"mediaType": "movie", "mediaId": 438631, "is4k": False},
        ),
        (
            {"tmdb_id": 90228, "media_type": "tv"},
            {"mediaType": "tv", "mediaId": 90228, "is4k": False, "seasons": "all"},
        ),
        (
            {"tmdb_id": 90228, "media_type": "tv", "seasons": "2, 1", "is_4k": True},
            {"mediaType": "tv", "mediaId": 90228, "is4k": True, "seasons": [1, 2]},
        ),
    ],
)
async def test_request(hass: HomeAssistant, entry, aioclient_mock, data, body) -> None:
    aioclient_mock.post(f"{API}/request", json={"id": 77}, status=201)
    resp = await hass.services.async_call(
        DOMAIN, "request", data, blocking=True, return_response=True
    )
    assert aioclient_mock.mock_calls[-1][2] == body
    assert resp["request_id"] == 77


async def test_request_rejected(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.post(f"{API}/request", json={"message": "Request for this media already exists."}, status=409)
    with pytest.raises(HomeAssistantError, match="already exists"):
        await hass.services.async_call(
            DOMAIN, "request", {"tmdb_id": 1, "media_type": "movie"}, blocking=True
        )


async def test_quick_request(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/search", json=SEARCH)
    aioclient_mock.post(f"{API}/request", json={"id": 5}, status=201)
    resp = await hass.services.async_call(
        DOMAIN, "quick_request", {"query": "dune"}, blocking=True, return_response=True
    )
    assert resp["requested"] is True and resp["tmdb_id"] == 438631


async def test_quick_request_already_available(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/search", json=SEARCH)
    resp = await hass.services.async_call(
        DOMAIN, "quick_request", {"query": "dune", "media_type": "tv"},
        blocking=True, return_response=True,
    )
    assert resp["requested"] is False and resp["status"] == "available"
    assert not any(call[0] == "POST" for call in aioclient_mock.mock_calls)


async def test_quick_request_no_results(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/search", json={"results": []})
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "quick_request", {"query": "zzz"}, blocking=True, return_response=True
        )
    assert err.value.translation_key == "no_results"


async def test_no_server(hass: HomeAssistant, entry) -> None:
    await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "search", {"query": "x"}, blocking=True, return_response=True
        )
    assert err.value.translation_key == "no_server"


async def test_strings_match_translations() -> None:
    assert (COMPONENT / "strings.json").read_bytes() == (COMPONENT / "translations" / "en.json").read_bytes()


async def test_exception_keys_exist() -> None:
    strings = json.loads((COMPONENT / "strings.json").read_text())
    source = "".join(p.read_text() for p in COMPONENT.glob("*.py"))
    import re
    used = set(re.findall(r'translation_key="(\w+)"', source))
    assert used <= set(strings["exceptions"])
