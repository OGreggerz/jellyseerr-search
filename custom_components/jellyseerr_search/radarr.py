"""Minimal async client for the Radarr v3 API, for the card's Waiting list:
release state and dates of wanted films, and whether copies are out there."""

from __future__ import annotations

from typing import Any

import aiohttp

from homeassistant.util.json import json_loads

from .const import REQUEST_TIMEOUT, SEARCH_TIMEOUT
from .sonarr import SonarrAuthError, SonarrConnectionError, SonarrError, SonarrNotFoundError, _error_message

# Same error kinds as Sonarr's (both are *arr apps with the same API style).
RadarrError = SonarrError
RadarrAuthError = SonarrAuthError
RadarrConnectionError = SonarrConnectionError
RadarrNotFoundError = SonarrNotFoundError


class RadarrClient:
    """Talks to one Radarr server."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        self._session = session
        self._base = url.rstrip("/") + "/api/v3"
        self._headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    async def _request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> Any:
        try:
            async with self._session.request(
                method, self._base + path, params=params, headers=self._headers, json=json,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status in (401, 403):
                    raise RadarrAuthError(f"HTTP {resp.status}")
                if resp.status == 404:
                    raise RadarrNotFoundError(await _error_message(resp))
                if resp.status >= 400:
                    raise RadarrError(await _error_message(resp))
                text = await resp.text()
                return json_loads(text) if text.strip() else None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RadarrConnectionError(str(err) or type(err).__name__) from err

    async def async_get_status(self) -> dict[str, Any]:
        """Also validates the key."""
        return await self._request("GET", "/system/status")

    async def async_get_movies(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/movie") or []

    async def async_get_movie_by_tmdb(self, tmdb_id: int) -> dict[str, Any] | None:
        found = await self._request("GET", "/movie", params={"tmdbId": tmdb_id}) or []
        return found[0] if found else None

    async def async_set_profile(self, movie_id: int, profile_id: int) -> None:
        """Change only the quality profile (Radarr's movie editor)."""
        await self._request("PUT", "/movie/editor", json={"movieIds": [movie_id], "qualityProfileId": profile_id})

    async def async_queued_movie_ids(self) -> set[int]:
        data = await self._request("GET", "/queue", params={"pageSize": 1000})
        return {r["movieId"] for r in (data or {}).get("records", []) if r.get("movieId")}

    async def async_releases(self, movie_id: int) -> list[dict[str, Any]]:
        """Radarr's interactive search: a live indexer search that grabs nothing."""
        return await self._request("GET", "/release", params={"movieId": movie_id}, timeout=SEARCH_TIMEOUT) or []

    async def async_search(self, movie_id: int) -> None:
        await self._request("POST", "/command", json={"name": "MoviesSearch", "movieIds": [movie_id]})
