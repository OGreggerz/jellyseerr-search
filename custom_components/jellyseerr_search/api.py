"""Minimal async client for the Jellyseerr v1 API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

import aiohttp
from yarl import URL

from .const import (
    MEDIA_STATUS,
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

    async def async_request(
        self,
        media_type: str,
        tmdb_id: int,
        seasons: list[int] | str | None = None,
        is_4k: bool = False,
    ) -> dict[str, Any]:
        """Ask Jellyseerr to fetch a movie or show. Returns the created request."""
        body: dict[str, Any] = {"mediaType": media_type, "mediaId": tmdb_id, "is4k": is_4k}
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
    }
