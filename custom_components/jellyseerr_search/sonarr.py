"""Minimal async client for the Sonarr v3 API, for the episode picker.

Jellyseerr requests whole seasons only, so picking single episodes and
following new ones has to go to Sonarr directly.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from homeassistant.util.json import json_loads

from .const import REQUEST_TIMEOUT, SEARCH_TIMEOUT


class SonarrError(Exception):
    """Sonarr answered with an error."""


class SonarrAuthError(SonarrError):
    """The API key was rejected."""


class SonarrNotFoundError(SonarrError):
    """No such series or episode (HTTP 404)."""


class SonarrConnectionError(SonarrError):
    """Sonarr could not be reached."""


class SonarrClient:
    """Talks to one Sonarr server."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        self._session = session
        self._base = url.rstrip("/") + "/api/v3"
        self._headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        timeout: int = REQUEST_TIMEOUT,
    ) -> Any:
        try:
            async with self._session.request(
                method,
                self._base + path,
                params=params,
                headers=self._headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status in (401, 403):
                    raise SonarrAuthError(f"HTTP {resp.status}")
                if resp.status == 404:
                    raise SonarrNotFoundError(await _error_message(resp))
                if resp.status >= 400:
                    raise SonarrError(await _error_message(resp))
                # Some Sonarr endpoints (DELETE, PUT /episode/monitor) answer with
                # an empty body.
                text = await resp.text()
                return json_loads(text) if text.strip() else None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SonarrConnectionError(str(err) or type(err).__name__) from err

    async def async_get_status(self) -> dict[str, Any]:
        """Also validates the key."""
        return await self._request("GET", "/system/status")

    async def async_get_series_by_tvdb(self, tvdb_id: int) -> dict[str, Any] | None:
        found = await self._request("GET", "/series", params={"tvdbId": tvdb_id})
        return found[0] if found else None

    async def async_lookup(self, tvdb_id: int) -> dict[str, Any] | None:
        found = await self._request("GET", "/series/lookup", params={"term": f"tvdb:{tvdb_id}"})
        return found[0] if found else None

    async def async_add_series(
        self, lookup: dict[str, Any], quality_profile_id: int, root_folder: str
    ) -> dict[str, Any]:
        """Add a show with nothing monitored and no search, so nothing downloads."""
        body = {
            **lookup,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder,
            "monitored": True,
            "monitorNewItems": "none",
            "seasonFolder": True,
            "seasons": [{**s, "monitored": False} for s in lookup.get("seasons", [])],
            "addOptions": {
                "monitor": "none",
                "searchForMissingEpisodes": False,
                "searchForCutoffUnmetEpisodes": False,
            },
        }
        return await self._request("POST", "/series", json=body)

    async def async_get_series(self, series_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/series/{series_id}")

    async def async_update_series(self, series: dict[str, Any]) -> dict[str, Any]:
        """PUT the whole series. Changing a season's `monitored` also sets every
        episode in it (Sonarr's SeriesService.UpdateSeries)."""
        return await self._request("PUT", f"/series/{series['id']}", json=series)

    async def async_delete_series(self, series_id: int) -> None:
        await self._request(
            "DELETE",
            f"/series/{series_id}",
            params={"deleteFiles": "true", "addImportListExclusion": "false"},
        )

    async def async_get_episodes(
        self, series_id: int, season_number: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"seriesId": series_id}
        if season_number is not None:
            params["seasonNumber"] = season_number
        return await self._request("GET", "/episode", params=params)

    async def async_get_episode_files(self, series_id: int) -> list[dict[str, Any]]:
        """The series' files, each with `mediaInfo` (audio and subtitle languages)."""
        return await self._request("GET", "/episodefile", params={"seriesId": series_id}) or []

    async def async_queued_episode_ids(self, series_id: int) -> set[int]:
        data = await self._request(
            "GET", "/queue", params={"seriesIds": series_id, "pageSize": 1000}
        )
        return {r["episodeId"] for r in (data or {}).get("records", []) if r.get("episodeId")}

    async def async_set_monitored(self, episode_ids: list[int], monitored: bool) -> None:
        if episode_ids:
            await self._request(
                "PUT", "/episode/monitor", json={"episodeIds": episode_ids, "monitored": monitored}
            )

    async def async_search_episodes(self, episode_ids: list[int]) -> None:
        if episode_ids:
            await self._request(
                "POST", "/command", json={"name": "EpisodeSearch", "episodeIds": episode_ids}
            )

    async def async_delete_episode_files(self, file_ids: list[int]) -> None:
        """Delete files from disk (Sonarr's recycle bin applies if set). Sonarr
        leaves the episodes monitored, so callers unmonitor them."""
        if file_ids:
            await self._request("DELETE", "/episodefile/bulk", json={"episodeFileIds": file_ids})

    async def async_release_matches(self, episode_id: int) -> bool:
        """Run Sonarr's interactive search for one episode (a live indexer search,
        so slow) and say whether any release was matched to it, approved or not.
        Tells whether the series type fits how the releases are named."""
        releases = await self._request(
            "GET", "/release", params={"episodeId": episode_id}, timeout=SEARCH_TIMEOUT
        )
        # Sonarr 4.0.20 leaves `episodeIds` null here; the match is in
        # `mappedEpisodeInfo` (checked live, 2026-10-23).
        return any(
            episode_id in (r.get("episodeIds") or [])
            or any(m.get("id") == episode_id for m in r.get("mappedEpisodeInfo") or [])
            for r in releases or []
        )

    async def async_first_profile_and_root(self) -> tuple[int, str]:
        """Fallback when Jellyseerr's Sonarr defaults can't be read."""
        profiles = await self._request("GET", "/qualityprofile")
        roots = await self._request("GET", "/rootfolder")
        if not profiles or not roots:
            raise SonarrError("Sonarr has no quality profile or root folder")
        return profiles[0]["id"], roots[0]["path"]


async def _error_message(resp: aiohttp.ClientResponse) -> str:
    try:
        data = await resp.json(content_type=None)
    except (aiohttp.ClientError, ValueError):
        data = None
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"])
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return str(data[0].get("errorMessage") or data[0])
    return f"HTTP {resp.status}"
