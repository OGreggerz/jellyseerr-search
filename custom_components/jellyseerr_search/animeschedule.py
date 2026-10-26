"""English dub dates from AnimeSchedule.net (API v3), for anime the card shows.

Only AnimeSchedule publishes dub air times in a form a program can read
(AniList, TVDB and TMDB carry Japanese broadcast dates only). Its terms:
requests carry an application token, results are cached only as needed, and
the app credits AnimeSchedule.net visibly (the card does, by every dub date).

The weekly dub timetable (`/timetables/dub`) is read for last week (for the
latest dubbed episode), this week and the next few, and kept for a few hours: a handful of requests a day, far inside
its 120 a minute. A show is matched by name, since AnimeSchedule has no TVDB
or TMDB ids: its names (title, English, romaji, native) are compared with the
show's names in Sonarr and Seerr, ignoring case and punctuation, and a
season suffix ("3rd Season", "Season 3") is allowed after them.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import re
from typing import Any
import unicodedata

import aiohttp

from homeassistant.util import dt as dt_util
from homeassistant.util.json import json_loads

from .const import REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://animeschedule.net/api/v3"
CREDIT_URL = "https://animeschedule.net"
WEEKS = range(-1, 4)  # last week, this week and the next three
CACHE_FOR = timedelta(hours=6)
RETRY_AFTER = timedelta(minutes=30)  # after a failure, don't ask again for this long
# A shorter name could match unrelated shows ("Slime" and "Slime Taoshite...").
MIN_NAME = 6


class AnimeScheduleError(Exception):
    """AnimeSchedule answered with an error or couldn't be reached."""


class AnimeScheduleClient:
    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async def async_dub_week(self, year: int, week: int) -> list[dict[str, Any]]:
        """One ISO week of the dub timetable, times in UTC."""
        try:
            async with self._session.get(
                f"{BASE_URL}/timetables/dub",
                params={"year": year, "week": week, "tz": "UTC"},
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status >= 400:
                    raise AnimeScheduleError(f"HTTP {resp.status}")
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AnimeScheduleError(str(err) or type(err).__name__) from err
        data = json_loads(text) if text.strip() else []
        return data if isinstance(data, list) else []


def normalise(name: str) -> str:
    """Lower case, accents and punctuation dropped: "The Apothecary Diaries!" →
    "theapothecarydiaries". Japanese script is kept as it is."""
    text = unicodedata.normalize("NFKD", name).casefold()
    return "".join(ch for ch in text if ch.isalnum() and not unicodedata.combining(ch))


# What may follow a show's name in a later season's entry.
_SEASON_SUFFIX = re.compile(r"^(\d+(st|nd|rd|th)?season|season\d+|part\d+|\d+|ii+|zokuhen)?$")


def names_match(entry: dict[str, Any], names: list[str]) -> bool:
    wanted = [n for n in (normalise(x) for x in names if x) if len(n) >= MIN_NAME]
    for field in ("title", "english", "romaji", "native"):
        have = normalise(entry.get(field) or "")
        for name in wanted:
            if have == name or (have.startswith(name) and _SEASON_SUFFIX.match(have[len(name):])):
                return True
    return False


def _delayed(entry: dict[str, Any], now: datetime) -> bool:
    """AnimeSchedule fills an undelayed entry's delayedUntil with
    0001-01-01T00:00:00Z (seen live: 46 of 50 entries in a week), and leaves
    past delays in place, so only a delay still running counts."""
    if entry.get("airingStatus") == "delayed-air":
        return True
    until = dt_util.parse_datetime(entry.get("delayedUntil") or "")
    return until is not None and until.year > 1 and until > now


class DubSchedule:
    """The next few weeks of the dub timetable, cached."""

    def __init__(self, client: AnimeScheduleClient) -> None:
        self._client = client
        self._entries: list[dict[str, Any]] = []
        self._fetched: datetime | None = None
        self._failed: datetime | None = None

    async def _async_entries(self, now: datetime) -> list[dict[str, Any]]:
        if self._fetched and now - self._fetched < CACHE_FOR:
            return self._entries
        if self._failed and now - self._failed < RETRY_AFTER:
            return self._entries
        entries: list[dict[str, Any]] = []
        try:
            for offset in WEEKS:
                year, week, _ = (now + timedelta(weeks=offset)).isocalendar()
                entries += await self._client.async_dub_week(year, week)
        except AnimeScheduleError as err:
            _LOGGER.warning("Couldn't read AnimeSchedule's dub timetable: %s", err)
            self._failed = now
            return self._entries
        self._entries, self._fetched, self._failed = entries, now, None
        return entries

    async def async_next_dub(self, names: list[str], now: datetime | None = None) -> dict[str, Any] | None:
        """The show's next English dub episode in the timetable, and the last
        one already out, or None if the show isn't in it (no dub airing in the
        next few weeks, or no dub at all)."""
        now = now or dt_util.utcnow()
        mine = [e for e in await self._async_entries(now) if names_match(e, names)]
        if not mine:
            return None
        dated = sorted(
            ((when, e) for e in mine if (when := dt_util.parse_datetime(e.get("episodeDate") or ""))),
            key=lambda pair: pair[0],
        )
        upcoming = [(w, e) for w, e in dated if w > now and e.get("airingStatus") != "aired"]
        aired = [(w, e) for w, e in dated if w <= now or e.get("airingStatus") == "aired"]
        if not upcoming and not aired:
            return None
        nxt = upcoming[0] if upcoming else None
        last = aired[-1] if aired else None
        return {
            "episode": nxt[1].get("episodeNumber") if nxt else None,
            "date_utc": nxt[0].isoformat() if nxt else None,
            "delayed": bool(nxt and _delayed(nxt[1], now)),
            "last_episode": last[1].get("episodeNumber") if last else None,
            "total": (nxt or last)[1].get("episodes") or None,
            "source": "AnimeSchedule.net",
            "url": f"{CREDIT_URL}/anime/{(nxt or last)[1].get('route')}" if (nxt or last)[1].get("route") else CREDIT_URL,
        }
