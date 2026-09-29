"""Shared test data."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jellyseerr_search.const import DOMAIN

URL = "http://jellyseerr.local:5055"
API = f"{URL}/api/v1"
DATA = {"url": URL, "api_key": "secret", "verify_ssl": True}

COUNTS = {
    "total": 12,
    "movie": 7,
    "tv": 5,
    "pending": 2,
    "approved": 1,
    "declined": 0,
    "processing": 3,
    "available": 6,
}

SEARCH = {
    "page": 1,
    "totalPages": 1,
    "totalResults": 3,
    "results": [
        {
            "id": 438631,
            "mediaType": "movie",
            "title": "Dune",
            "releaseDate": "2021-09-15",
            "overview": "Paul Atreides...",
            "posterPath": "/d5NXSklXo0qyIYkgV94XAgMIckC.jpg",
        },
        {"id": 1, "mediaType": "person", "name": "Frank Herbert"},
        {
            "id": 90228,
            "mediaType": "tv",
            "name": "Dune: Prophecy",
            "firstAirDate": "2024-11-17",
            "mediaInfo": {"status": 5},
        },
    ],
}


def mock_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title="Jellyseerr", data=DATA, unique_id=URL)
