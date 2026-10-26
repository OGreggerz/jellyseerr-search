"""Minimal async client for the Jellyseerr v1 API."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote, urlencode

import aiohttp
from yarl import URL

from .const import (
    LIBRARY_CONCURRENCY,
    MEDIA_MOVIE,
    MEDIA_STATUS,
    POPULAR_TV_MIN_VOTES,
    MEDIA_TYPES,
    REQUEST_TIMEOUT,
    STATUS_NOT_REQUESTED,
    TMDB_POSTER_URL,
)


class JellyseerrError(Exception):
    """Jellyseerr answered with an error."""


class JellyseerrAuthError(JellyseerrError):
    """The API key was rejected."""


class JellyseerrConnectionError(JellyseerrError):
    """Jellyseerr could not be reached."""


class JellyseerrClient:
    """Talks to one Jellyseerr server."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        self._session = session
        self._base = url.rstrip("/") + "/api/v1"
        self._headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = self._base + path
        if params:
            # Jellyseerr rejects "+" for spaces and unescaped reserved characters,
            # so encode everything the way encodeURIComponent would.
            url += "?" + urlencode(params, quote_via=quote, safe="")
        try:
            async with self._session.request(
                method,
                URL(url, encoded=True),
                headers=self._headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status in (401, 403):
                    raise JellyseerrAuthError(f"HTTP {resp.status}")
                if resp.status >= 400:
                    raise JellyseerrError(await _error_message(resp))
                if resp.status == 204:
                    return None
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise JellyseerrConnectionError(str(err) or type(err).__name__) from err

    async def async_get_me(self) -> dict[str, Any]:
        """The user the API key belongs to. Also validates the key."""
        return await self._request("GET", "/auth/me")

    async def async_get_request_counts(self) -> dict[str, int]:
        return await self._request("GET", "/request/count")

    async def async_search(self, query: str, page: int = 1) -> list[dict[str, Any]]:
        """Movies and shows matching `query`, normalized. People are dropped."""
        data = await self._request("GET", "/search", params={"query": query, "page": page})
        return [
            normalize_result(item)
            for item in data.get("results", [])
            if item.get("mediaType") in MEDIA_TYPES
        ]

    async def async_trending(self, media_type: str, page: int = 1) -> list[dict[str, Any]]:
        """Trending titles (TMDB, past day), normalized. `media_type` is all, movie
        or tv; Seerr filters by it. People and collections are dropped."""
        data = await self._request(
            "GET", "/discover/trending", params={"mediaType": media_type, "page": page}
        )
        return [
            normalize_result(item)
            for item in data.get("results", [])
            if item.get("mediaType") in MEDIA_TYPES
        ]

    async def async_popular(self, media_type: str, page: int = 1) -> list[dict[str, Any]]:
        """Popular movies or shows (TMDB discover, by popularity), normalized.
        Jellyseerr has no combined list, so `media_type` is movie or tv. Shows
        need POPULAR_TV_MIN_VOTES votes."""
        if media_type == MEDIA_MOVIE:
            path, params = "/discover/movies", {"page": page}
        else:
            path, params = "/discover/tv", {"page": page, "voteCountGte": POPULAR_TV_MIN_VOTES}
        data = await self._request("GET", path, params=params)
        return [
            normalize_result(item)
            for item in data.get("results", [])
            if item.get("mediaType") in MEDIA_TYPES
        ]

    async def async_library(self, limit: int) -> list[dict[str, Any]]:
        """What the server has (available or partly available), newest first,
        normalized like search hits. Jellyseerr's /media list has no titles or
        posters, so each title's details are fetched too (a few at a time)."""
        data = await self._request(
            "GET", "/media", params={"filter": "allavailable", "sort": "mediaAdded", "take": limit, "skip": 0}
        )
        items = [m for m in data.get("results", []) if m.get("mediaType") in MEDIA_TYPES and m.get("tmdbId")]
        gate = asyncio.Semaphore(LIBRARY_CONCURRENCY)

        async def details(media: dict[str, Any]) -> dict[str, Any] | None:
            async with gate:
                try:
                    found = await self._request("GET", f"/{media['mediaType']}/{media['tmdbId']}")
                except JellyseerrError:
                    return None  # One title's details failing shouldn't hide the rest.
            return normalize_result({**found, "mediaType": media["mediaType"], "mediaInfo": found.get("mediaInfo") or media})

        return [r for r in await asyncio.gather(*(details(m) for m in items)) if r]

    async def async_get_tv_seasons(self, tmdb_id: int) -> list[dict[str, Any]]:
        """A show's seasons (specials excluded) with what the server has of each."""
        data = await self._request("GET", f"/tv/{tmdb_id}")
        have = {
            season["seasonNumber"]: season.get("status")
            for season in (data.get("mediaInfo") or {}).get("seasons", [])
        }
        return [
            {
                "season_number": season["seasonNumber"],
                "name": season.get("name") or f"Season {season['seasonNumber']}",
                "episode_count": season.get("episodeCount", 0),
                "status": MEDIA_STATUS.get(have.get(season["seasonNumber"]), STATUS_NOT_REQUESTED),
            }
            for season in data.get("seasons", [])
            if season.get("seasonNumber", 0) > 0
        ]

    async def async_release_info(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        """Whether a title is out, from TMDB via Jellyseerr. Films: TMDB status and
        the cinema (types 2-3), digital (4) and physical (5) release dates, UK
        first, then US, then the earliest anywhere. Shows: TMDB status and the
        next and last episode air dates."""
        data = await self._request("GET", f"/{media_type}/{tmdb_id}")
        if media_type != MEDIA_MOVIE:
            return {
                "tmdb_status": data.get("status"),
                "next_air_date": (data.get("nextEpisodeToAir") or {}).get("airDate"),
                "last_air_date": (data.get("lastEpisodeToAir") or {}).get("airDate") or data.get("lastAirDate"),
            }
        by_country = {
            r.get("iso_3166_1"): r.get("release_dates") or [] for r in (data.get("releases") or {}).get("results", [])
        }

        def first(types: tuple[int, ...]) -> str | None:
            for country in ("GB", "US"):
                dates = sorted(d["release_date"][:10] for d in by_country.get(country, []) if d.get("type") in types)
                if dates:
                    return dates[0]
            anywhere = sorted(
                d["release_date"][:10] for dates in by_country.values() for d in dates if d.get("type") in types
            )
            return anywhere[0] if anywhere else None

        return {
            "tmdb_status": data.get("status"),
            "theatrical": first((2, 3)),
            "digital": first((4,)),
            "physical": first((5,)),
        }

    async def async_get_tvdb_id(self, tmdb_id: int) -> int | None:
        """The show's TVDB id, which Sonarr matches on (Sonarr may have no TMDB id)."""
        data = await self._request("GET", f"/tv/{tmdb_id}")
        return (data.get("externalIds") or {}).get("tvdbId") or None

    async def async_get_details(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        """Seerr's details of a film or show (TMDB's, with keywords and genres)."""
        return await self._request("GET", f"/{media_type}/{tmdb_id}") or {}

    async def async_get_sonarr_defaults(self, anime: bool = False) -> tuple[int, str] | None:
        """Quality profile id and root folder of Jellyseerr's default (non-4K) Sonarr,
        so shows added by the episode picker land where requests do. For anime,
        Seerr's anime profile and folder, as Seerr itself uses for anime (each
        falls back to the normal one if unset)."""
        servers = await self._request("GET", "/settings/sonarr") or []
        hd = [s for s in servers if not s.get("is4k")]
        server = next((s for s in hd if s.get("isDefault")), hd[0] if hd else None)
        if not server or not server.get("activeProfileId") or not server.get("activeDirectory"):
            return None
        if anime:
            return (
                int(server.get("activeAnimeProfileId") or server["activeProfileId"]),
                str(server.get("activeAnimeDirectory") or server["activeDirectory"]),
            )
        return int(server["activeProfileId"]), str(server["activeDirectory"])

    async def async_forget(self, media_type: str, tmdb_id: int, keep_requests: bool = False) -> bool:
        """Drop Jellyseerr's record of a title whose files are already gone, so
        it reads as not requested now rather than after Jellyseerr's nightly
        availability sync. Deleting the record deletes its requests too
        (cascade), so with `keep_requests` a requested title is left for that
        sync, which marks it deleted and keeps the history. False if nothing
        was dropped."""
        data = await self._request("GET", f"/{media_type}/{tmdb_id}")
        info = data.get("mediaInfo") or {}
        media_id = info.get("id")
        if not media_id or (keep_requests and info.get("requests")):
            return False
        await self._request("DELETE", f"/media/{media_id}")
        return True

    async def async_remove(self, media_type: str, tmdb_id: int) -> bool:
        """Delete a movie or a whole show from Radarr/Sonarr, files included, the
        way Jellyseerr's "Remove from Radarr/Sonarr" button does. Jellyseerr then
        marks it deleted, so it can be requested again. False if Jellyseerr has
        no record of it."""
        data = await self._request("GET", f"/{media_type}/{tmdb_id}")
        media_id = (data.get("mediaInfo") or {}).get("id")
        if not media_id:
            return False
        await self._request("DELETE", f"/media/{media_id}/file", params={"is4k": "false"})
        return True

    async def async_request(
        self,
        media_type: str,
        tmdb_id: int,
        seasons: list[int] | str | None = None,
        is_4k: bool = False,
        profile_id: int | None = None,
    ) -> dict[str, Any]:
        """Ask Jellyseerr to fetch a movie or show. Returns the created request.
        `profile_id` overrides the server's quality profile (Seerr applies it
        for admins, as its Advanced options do)."""
        body: dict[str, Any] = {"mediaType": media_type, "mediaId": tmdb_id, "is4k": is_4k}
        if profile_id is not None:
            body["profileId"] = profile_id
        if media_type == "tv":
            body["seasons"] = seasons if seasons else "all"
        return await self._request("POST", "/request", json=body)


async def _error_message(resp: aiohttp.ClientResponse) -> str:
    try:
        data = await resp.json(content_type=None)
    except (aiohttp.ClientError, ValueError):
        data = None
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"])
    return f"HTTP {resp.status}"


def normalize_result(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Jellyseerr search hit into what services and the card need."""
    date = item.get("releaseDate") or item.get("firstAirDate") or ""
    media_info = item.get("mediaInfo") or {}
    poster = item.get("posterPath")
    return {
        "tmdb_id": item["id"],
        "media_type": item["mediaType"],
        "title": item.get("title") or item.get("name") or "",
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "overview": item.get("overview") or "",
        "poster_url": f"{TMDB_POSTER_URL}{poster}" if poster else None,
        "status": MEDIA_STATUS.get(media_info.get("status"), STATUS_NOT_REQUESTED)
        if media_info
        else STATUS_NOT_REQUESTED,
        # For matching shows Sonarr knows without a TMDB id.
        "tvdb_id": media_info.get("tvdbId") or None,
    }
