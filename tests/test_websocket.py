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
    assert msg["result"] == {"version": CARD_VERSION, "waiting": False}


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


async def test_trending(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/discover/trending", json=SEARCH)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/trending"})
    msg = await ws.receive_json()
    assert msg["success"]
    # The person in the fixture is dropped.
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [438631, 90228]
    assert msg["result"]["results"][1]["status"] == "available"
    assert dict(aioclient_mock.mock_calls[-1][1].query) == {"mediaType": "all", "page": "1"}


async def test_trending_filters_type(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Seerr filters by mediaType; a server that ignores it is filtered here."""
    aioclient_mock.get(f"{API}/discover/trending", json=SEARCH)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/trending", "media_type": "tv"})
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [90228]
    assert dict(aioclient_mock.mock_calls[-1][1].query) == {"mediaType": "tv", "page": "1"}


async def test_trending_rejects_unknown_type(hass: HomeAssistant, entry, hass_ws_client) -> None:
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/trending", "media_type": "person"})
    msg = await ws.receive_json()
    assert not msg["success"]


MOVIES = {"results": [{"id": 1, "mediaType": "movie", "title": "A"}, {"id": 2, "mediaType": "movie", "title": "B"}]}
SHOWS = {"results": [{"id": 3, "mediaType": "tv", "name": "C", "mediaInfo": {"status": 4}}]}


async def test_popular_all_alternates(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    aioclient_mock.get(f"{API}/discover/tv", json=SHOWS)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/popular"})
    msg = await ws.receive_json()
    assert msg["success"]
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [1, 3, 2]
    assert msg["result"]["results"][1]["status"] == "partially_available"


async def test_popular_one_type(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/discover/tv", json=SHOWS)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/popular", "media_type": "tv"})
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [3]
    # Only the TV list is fetched (other calls are the sensors' /request/count).
    urls = [call[1] for call in aioclient_mock.mock_calls]
    tv = [url for url in urls if url.path == "/api/v1/discover/tv"]
    assert tv and not any(url.path == "/api/v1/discover/movies" for url in urls)
    # Low-vote shows (foreign daily news, soaps) are filtered out by Seerr.
    assert dict(tv[-1].query) == {"page": "1", "voteCountGte": "500"}


def _discover_calls(aioclient_mock, path: str) -> list[dict[str, str]]:
    return [dict(call[1].query) for call in aioclient_mock.mock_calls if call[1].path == f"/api/v1/discover/{path}"]


async def test_discover_one_service(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/discover/tv", json={**SHOWS, "totalPages": 3})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "media_type": "tv"}
    )
    msg = await ws.receive_json()
    assert msg["success"]
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [3]
    assert msg["result"]["has_more"] is True
    assert not _discover_calls(aioclient_mock, "movies")
    # Popular by default; with no genre the stricter vote floor keeps obscure titles out.
    assert _discover_calls(aioclient_mock, "tv") == [
        {"page": "1", "watchProviders": "8", "watchRegion": "GB", "sortBy": "popularity.desc", "voteCountGte": "500"}
    ]


async def test_discover_all_alternates_and_pages(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Show more asks for the next page of both lists; the last page ends it."""
    aioclient_mock.get(f"{API}/discover/movies", json={**MOVIES, "totalPages": 2})
    aioclient_mock.get(f"{API}/discover/tv", json={**SHOWS, "totalPages": 1})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "page": 2})
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [1, 3, 2]
    assert msg["result"]["has_more"] is False
    assert _discover_calls(aioclient_mock, "movies")[-1]["page"] == "2"
    assert _discover_calls(aioclient_mock, "tv")[-1]["page"] == "2"


async def test_discover_sort_and_genre_per_type(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Film and TV genre ids differ, as do the date sorts; a genre lowers the floor."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    aioclient_mock.get(f"{API}/discover/tv", json=SHOWS)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 283, "region": "GB", "sort": "newest", "genre": "action"}
    )
    msg = await ws.receive_json()
    assert msg["success"]
    movie = _discover_calls(aioclient_mock, "movies")[-1]
    tv = _discover_calls(aioclient_mock, "tv")[-1]
    assert (movie["sortBy"], movie["genre"], movie["voteCountGte"]) == ("primary_release_date.desc", "28|12", "50")
    assert (tv["sortBy"], tv["genre"], tv["voteCountGte"]) == ("first_air_date.desc", "10759", "50")


async def test_discover_genre_with_floor(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "media_type": "movie",
         "sort": "top_rated", "genre": "comedy"}
    )
    await ws.receive_json()
    call = _discover_calls(aioclient_mock, "movies")[-1]
    assert (call["sortBy"], call["genre"], call["voteCountGte"]) == ("vote_average.desc", "35", "200")


async def test_discover_genre_missing_for_one_type(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Horror has no TV genre: All fetches only films, TV fetches nothing."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "genre": "horror"})
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [1, 2]
    assert not _discover_calls(aioclient_mock, "tv")

    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "genre": "horror", "media_type": "tv"}
    )
    msg = await ws.receive_json()
    assert msg["result"] == {"results": [], "has_more": False}
    assert not _discover_calls(aioclient_mock, "tv")


async def test_discover_stops_at_tmdbs_last_page(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """TMDB serves 500 pages at most, whatever totalPages says."""
    aioclient_mock.get(f"{API}/discover/tv", json={**SHOWS, "totalPages": 900})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "media_type": "tv", "page": 500}
    )
    msg = await ws.receive_json()
    assert msg["result"]["has_more"] is False


async def test_discover_brand_per_type(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    """Disney: films by studio, TV by original network; a brand list has no vote floor."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    aioclient_mock.get(f"{API}/discover/tv", json=SHOWS)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "brand": "disney"})
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [1, 3, 2]
    movie = _discover_calls(aioclient_mock, "movies")[-1]
    tv = _discover_calls(aioclient_mock, "tv")[-1]
    assert (movie["studio"], movie["voteCountGte"]) == ("2", "0")
    assert (tv["network"], tv["voteCountGte"]) == ("54", "0")
    assert "studio" not in tv  # Seerr's /discover/tv rejects it.


async def test_discover_brand_films_only(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    """Star Wars TV can't be picked out, so All lists the films and TV lists nothing."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "brand": "starwars", "sort": "top_rated"}
    )
    msg = await ws.receive_json()
    assert [r["tmdb_id"] for r in msg["result"]["results"]] == [1, 2]
    assert not _discover_calls(aioclient_mock, "tv")
    call = _discover_calls(aioclient_mock, "movies")[-1]
    # Top rated keeps a small floor even for a brand, so one 10/10 vote can't lead it.
    assert (call["studio"], call["sortBy"], call["voteCountGte"]) == ("1", "vote_average.desc", "20")

    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "brand": "starwars", "media_type": "tv"}
    )
    msg = await ws.receive_json()
    assert msg["result"] == {"results": [], "has_more": False}


async def test_discover_brand_with_genre(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    """Marvel TV by keyword, narrowed by a genre; the brand's floor wins over the genre's."""
    aioclient_mock.get(f"{API}/discover/tv", json=SHOWS)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "brand": "marvel",
         "genre": "action", "media_type": "tv"}
    )
    await ws.receive_json()
    call = _discover_calls(aioclient_mock, "tv")[-1]
    assert (call["keywords"], call["genre"], call["voteCountGte"]) == ("180547", "10759", "0")


async def test_discover_christmas_is_a_keyword(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Christmas is TMDB's keyword, with its own lower floor (a genre's 200 cut real
    Christmas films); with Marvel, both keywords must match."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 8, "region": "GB", "genre": "christmas", "media_type": "movie"}
    )
    await ws.receive_json()
    call = _discover_calls(aioclient_mock, "movies")[-1]
    assert (call["keywords"], call["voteCountGte"]) == ("207317", "50")
    assert "genre" not in call

    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": 337, "region": "GB", "genre": "christmas",
         "brand": "marvel", "media_type": "movie"}
    )
    await ws.receive_json()
    call = _discover_calls(aioclient_mock, "movies")[-1]
    assert (call["keywords"], call["voteCountGte"]) == ("207317,180547", "0")


async def test_discover_any_of_several_services(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """The card's All: titles on any of its services ("|" is TMDB's any-of)."""
    aioclient_mock.get(f"{API}/discover/movies", json=MOVIES)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/discover", "provider": [8, 337, 283], "region": "GB",
         "genre": "christmas", "media_type": "movie"}
    )
    msg = await ws.receive_json()
    assert msg["success"]
    assert _discover_calls(aioclient_mock, "movies")[-1]["watchProviders"] == "8|337|283"


async def test_discover_rejects_bad_input(hass: HomeAssistant, entry, hass_ws_client) -> None:
    ws = await hass_ws_client(hass)
    for bad in (
        {"region": "GB", "provider": 0},
        {"region": "gb", "provider": 8},
        {"region": "GB", "provider": 8, "sort": "random"},
        {"region": "GB", "provider": 8, "genre": "western"},
        {"region": "GB", "provider": 337, "brand": "dreamworks"},
        {"region": "GB", "provider": []},
        {"region": "GB", "provider": [8, 0]},
        {"region": "GB", "provider": 8, "page": 501},
    ):
        await ws.send_json_auto_id({"type": f"{DOMAIN}/discover", **bad})
        msg = await ws.receive_json()
        assert not msg["success"], bad


async def test_remove(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/movie/438631", json={"id": 438631, "mediaInfo": {"id": 12, "status": 5}})
    aioclient_mock.delete(f"{API}/media/12/file", status=204)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/remove", "tmdb_id": 438631, "media_type": "movie"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"] == {"tmdb_id": 438631, "media_type": "movie"}
    method, url = aioclient_mock.mock_calls[-1][0], aioclient_mock.mock_calls[-1][1]
    assert method == "DELETE" and url.path == "/api/v1/media/12/file"
    assert dict(url.query) == {"is4k": "false"}


async def test_remove_unknown_title(
    hass: HomeAssistant, entry, aioclient_mock, hass_ws_client
) -> None:
    """Nothing in Jellyseerr's database: report it rather than calling delete."""
    aioclient_mock.get(f"{API}/tv/1", json={"id": 1})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/remove", "tmdb_id": 1, "media_type": "tv"})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert not any(call[0] == "DELETE" for call in aioclient_mock.mock_calls)


async def test_library(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(
        f"{API}/media",
        json={
            "pageInfo": {"results": 3},
            "results": [
                {"tmdbId": 90228, "mediaType": "tv", "status": 4},
                {"tmdbId": 438631, "mediaType": "movie", "status": 5},
                {"tmdbId": 5, "mediaType": "movie", "status": 5},
            ],
        },
    )
    aioclient_mock.get(f"{API}/tv/90228", json={"id": 90228, "name": "Dune: Prophecy", "firstAirDate": "2024-11-17", "mediaInfo": {"status": 4}})
    aioclient_mock.get(f"{API}/movie/438631", json={"id": 438631, "title": "Dune", "releaseDate": "2021-09-15", "posterPath": "/p.jpg", "mediaInfo": {"status": 5}})
    aioclient_mock.get(f"{API}/movie/5", status=500)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/library"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert [(r["title"], r["media_type"], r["status"]) for r in msg["result"]["results"]] == [
        ("Dune: Prophecy", "tv", "partially_available"),
        ("Dune", "movie", "available"),
    ]
    media_call = next(c for c in aioclient_mock.mock_calls if c[1].path == "/api/v1/media")
    assert dict(media_call[1].query) == {
        "filter": "allavailable",
        "sort": "mediaAdded",
        "take": "60",
        "skip": "0",
    }


async def test_release_info_film(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/movie/1727734", json={
        "status": "Released",
        "releases": {"results": [
            {"iso_3166_1": "US", "release_dates": [{"type": 2, "release_date": "2026-10-23T00:00:00.000Z"}, {"type": 4, "release_date": "2026-12-01T00:00:00.000Z"}]},
            {"iso_3166_1": "GB", "release_dates": [{"type": 3, "release_date": "2026-10-22T00:00:00.000Z"}]},
            {"iso_3166_1": "DE", "release_dates": [{"type": 5, "release_date": "2027-02-01T00:00:00.000Z"}]},
        ]},
    })
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/release", "tmdb_id": 1727734, "media_type": "movie"})
    result = (await ws.receive_json())["result"]
    # UK first for cinema; no UK digital, so US; physical only in Germany.
    release = {k: result[k] for k in ("tmdb_status", "theatrical", "digital", "physical")}
    assert release == {"tmdb_status": "Released", "theatrical": "2026-10-22", "digital": "2026-12-01", "physical": "2027-02-01"}


async def test_release_info_show(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    aioclient_mock.get(f"{API}/tv/220542", json={
        "status": "Returning Series", "nextEpisodeToAir": {"airDate": "2026-10-23"}, "lastEpisodeToAir": {"airDate": "2026-10-16"},
    })
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/release", "tmdb_id": 220542, "media_type": "tv"})
    result = (await ws.receive_json())["result"]
    assert {k: result[k] for k in ("tmdb_status", "next_air_date", "last_air_date")} == {
        "tmdb_status": "Returning Series", "next_air_date": "2026-10-23", "last_air_date": "2026-10-16",
    }
    # A record with none of the extras gives empty ones, not errors.
    assert (result["cast"], result["trailer"], result["credit"], result["rating"]) == ([], None, None, None)


async def test_title_details_film(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    """Cast, director, facts and the trailer, from the same record as the dates.
    Videos as Seerr lists Coco's (2026-10-30): featurettes and clips first."""
    aioclient_mock.get(f"{API}/movie/354912", json={
        "status": "Released", "runtime": 105, "voteAverage": 8.213, "voteCount": 21000,
        "tagline": "The celebration of a lifetime.",
        "genres": [{"id": 10751, "name": "Family"}, {"id": 16, "name": "Animation"}],
        "credits": {
            "cast": [
                {"name": "Gael García Bernal", "character": "Héctor (voice)", "order": 1, "profilePath": "/g.jpg"},
                {"name": "Anthony Gonzalez", "character": "Miguel Rivera (voice)", "order": 0, "profilePath": None},
            ],
            "crew": [
                {"name": "Lee Unkrich", "job": "Director"},
                {"name": "Lee Unkrich", "job": "Director"},
                {"name": "Seong-Young Kim", "job": "Layout"},
            ],
        },
        "relatedVideos": [
            {"site": "YouTube", "key": "kmFZc7mdEec", "type": "Featurette", "name": "Making Tamales"},
            {"site": "YouTube", "key": "yg8116aeD7E", "type": "Clip", "name": "Un Poco Loco"},
            {"site": "YouTube", "key": "teaser1", "type": "Teaser", "name": "Teaser"},
            {"site": "Vimeo", "key": "vimeo1", "type": "Trailer", "name": "Official Trailer"},
            {"site": "YouTube", "key": "trailer1", "type": "Trailer", "name": "Trailer"},
            {"site": "YouTube", "key": "Rvr68u6k5sI", "type": "Trailer", "name": "Official Final Trailer"},
        ],
    })
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/release", "tmdb_id": 354912, "media_type": "movie"})
    result = (await ws.receive_json())["result"]
    assert (result["runtime"], result["genres"], result["rating"]) == (105, ["Family", "Animation"], 8.2)
    assert result["credit"] == {"label": "Directed by", "names": ["Lee Unkrich"]}
    assert [c["name"] for c in result["cast"]] == ["Anthony Gonzalez", "Gael García Bernal"]
    assert result["cast"][0]["photo_url"] is None
    assert result["cast"][1]["photo_url"] == "https://image.tmdb.org/t/p/w185/g.jpg"
    # YouTube only, a Trailer before a Teaser, an official one first.
    assert result["trailer"] == {"key": "Rvr68u6k5sI", "name": "Official Final Trailer"}


async def test_title_details_show(hass: HomeAssistant, entry, aioclient_mock, hass_ws_client) -> None:
    """Shows: creator, seasons, episode length; few votes means no rating; a teaser if no trailer."""
    aioclient_mock.get(f"{API}/tv/83867", json={
        "status": "Ended", "numberOfSeasons": 2, "episodeRunTime": [45], "voteAverage": 9.9, "voteCount": 3,
        "createdBy": [{"name": "Tony Gilroy"}],
        "relatedVideos": [{"site": "YouTube", "key": "t1", "type": "Teaser", "name": "Teaser"}],
    })
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/release", "tmdb_id": 83867, "media_type": "tv"})
    result = (await ws.receive_json())["result"]
    assert (result["seasons_count"], result["runtime"], result["rating"]) == (2, 45, None)
    assert result["credit"] == {"label": "Created by", "names": ["Tony Gilroy"]}
    assert result["trailer"] == {"key": "t1", "name": "Teaser"}
