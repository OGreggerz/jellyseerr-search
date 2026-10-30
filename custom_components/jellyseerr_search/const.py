"""Constants for the Jellyseerr Search integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "jellyseerr_search"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)
REQUEST_TIMEOUT: Final = 15
# Sonarr's interactive search waits for the indexers.
SEARCH_TIMEOUT: Final = 90

TMDB_POSTER_URL: Final = "https://image.tmdb.org/t/p/w342"

MEDIA_MOVIE: Final = "movie"
MEDIA_TV: Final = "tv"
MEDIA_TYPES: Final = (MEDIA_MOVIE, MEDIA_TV)

# Jellyseerr's MediaStatus enum. Anything with no mediaInfo was never requested.
MEDIA_STATUS: Final = {
    1: "unknown",
    2: "pending",
    3: "processing",
    4: "partially_available",
    5: "available",
    6: "blacklisted",
    7: "deleted",
}
STATUS_NOT_REQUESTED: Final = "not_requested"
# Popular TV skips shows with fewer TMDB votes than this. TMDB's TV popularity
# is full of daily news and soaps from every country (a news bulletin with 2
# votes ranks beside Breaking Bad); 200 still let some through. Movies aren't
# filtered: unreleased blockbusters have 0 votes and lead the popular list.
POPULAR_TV_MIN_VOTES: Final = 500

# Streaming browse: one service's catalogue in one country (TMDB discover with
# watch providers, through Seerr). Seerr's sortBy values differ by type for dates.
BROWSE_SORTS: Final = {
    "popular": {MEDIA_MOVIE: "popularity.desc", MEDIA_TV: "popularity.desc"},
    "top_rated": {MEDIA_MOVIE: "vote_average.desc", MEDIA_TV: "vote_average.desc"},
    "newest": {MEDIA_MOVIE: "primary_release_date.desc", MEDIA_TV: "first_air_date.desc"},
}
# Fewest TMDB votes a title needs, as (no genre, with a genre). Read against UK
# Netflix 2026-10-30: popular films with no floor include 8-10 vote releases, and
# a genre narrows the list enough that 200 is clean. Newest needs a low floor or
# it hides the month's releases (a new show has tens of votes, not hundreds).
BROWSE_MIN_VOTES: Final = {"popular": (500, 200), "top_rated": (500, 200), "newest": (50, 50)}
# The genres the card offers, as TMDB genre ids per type ("|" = any of). Film and
# TV lists differ (TV has "Action & Adventure", film has Action and Adventure);
# None means the type has no such genre. The card's GENRES must list the same keys.
BROWSE_GENRES: Final[dict[str, dict[str, str | None]]] = {
    "action": {MEDIA_MOVIE: "28|12", MEDIA_TV: "10759"},
    "animation": {MEDIA_MOVIE: "16", MEDIA_TV: "16"},
    "comedy": {MEDIA_MOVIE: "35", MEDIA_TV: "35"},
    "crime": {MEDIA_MOVIE: "80", MEDIA_TV: "80"},
    "documentary": {MEDIA_MOVIE: "99", MEDIA_TV: "99"},
    "drama": {MEDIA_MOVIE: "18", MEDIA_TV: "18"},
    "family": {MEDIA_MOVIE: "10751", MEDIA_TV: "10751|10762"},
    "horror": {MEDIA_MOVIE: "27", MEDIA_TV: None},
    "mystery": {MEDIA_MOVIE: "9648|53", MEDIA_TV: "9648"},
    "romance": {MEDIA_MOVIE: "10749", MEDIA_TV: None},
    "scifi": {MEDIA_MOVIE: "878|14", MEDIA_TV: "10765"},
    "reality": {MEDIA_MOVIE: None, MEDIA_TV: "10764"},
}
# TMDB serves at most this many pages of a discover list.
BROWSE_MAX_PAGE: Final = 500

# Episode picker (optional; Sonarr directly, since Jellyseerr requests whole seasons).
CONF_SONARR_URL: Final = "sonarr_url"
CONF_SONARR_API_KEY: Final = "sonarr_api_key"
# Optional Radarr, for films in the Waiting list.
CONF_RADARR_URL: Final = "radarr_url"
CONF_RADARR_API_KEY: Final = "radarr_api_key"
# Optional AnimeSchedule.net application token, for English dub dates.
CONF_ANIMESCHEDULE_TOKEN: Final = "animeschedule_token"
# Sonarr fills in a newly added show's episodes in the background (about a second
# on Sonarr 4.0.20); wait up to this long for them.
EPISODE_WAIT_SECONDS: Final = 15

# The card's Downloaded list: newest this many, details fetched this many at a time.
LIBRARY_LIMIT: Final = 60
LIBRARY_CONCURRENCY: Final = 6

# Statuses a new request makes sense for.
REQUESTABLE_STATUSES: Final = (STATUS_NOT_REQUESTED, "unknown", "deleted")

# Keys of GET /api/v1/request/count that become sensors.
REQUEST_COUNT_KEYS: Final = ("pending", "approved", "processing", "available", "total")

# The card is served from here and registered as a Lovelace resource with
# `?v=CARD_VERSION` appended. Keep CARD_VERSION equal to manifest.json's version.
URL_BASE: Final = f"/{DOMAIN}"
CARD_FILENAME: Final = "jellyseerr-search-card.js"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"
CARD_VERSION: Final = "0.13.0"
