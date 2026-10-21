# Jellyseerr Search for Home Assistant

Search for movies and TV shows from Home Assistant and request them through
[Jellyseerr](https://github.com/Fallenbagel/jellyseerr), which hands them to
Radarr/Sonarr and on to your download client.

## Install

HACS → Integrations → ⋮ → Custom repositories → add this repo as an
*Integration*, install **Jellyseerr Search**, restart, then
Settings → Devices & services → Add integration → **Jellyseerr Search**.
You need the Jellyseerr URL (e.g. `http://192.168.1.20:5055`) and the API key
from Jellyseerr → Settings → General.

## What you get

**Search card**: the integration adds `custom:jellyseerr-search-card` to your
dashboard resources automatically (storage-mode dashboards). Add it from
*Add card → Jellyseerr Search*. Before you type it shows what's trending today, or
what's popular (switch on the heading; follows the All / Movies / TV filter). Type a title, tap a poster, pick seasons for
shows, and tap **Request**. Posters show whether a title is already requested
or available.

```yaml
type: custom:jellyseerr-search-card
title: Request movies & TV
media_type: all      # default filter: all | movie | tv
show_4k: false       # offer a 4K toggle (needs 4K Radarr/Sonarr in Jellyseerr)
show_trending: true  # trending / popular titles while the search box is empty
```

If your dashboards are in YAML mode, add `/jellyseerr_search/jellyseerr-search-card.js`
as a JavaScript module resource yourself.

**Sensors**: pending, approved, processing, available and total request counts.

**Actions**

| Action | Does |
|---|---|
| `jellyseerr_search.search` | Returns matches: `tmdb_id`, `media_type`, `title`, `year`, `overview`, `poster_url`, `status` |
| `jellyseerr_search.request` | Requests a `tmdb_id` (TV: `seasons: all` or `"1, 2"`; optional `is_4k`) |
| `jellyseerr_search.quick_request` | Searches and requests the top match; skips titles already requested/available |

```yaml
action: jellyseerr_search.search
data:
  query: The Expanse
  media_type: tv
response_variable: found
```

### Voice: "request Dune"

```yaml
triggers:
  - trigger: conversation
    command: "request {title}"
actions:
  - action: jellyseerr_search.quick_request
    data:
      query: "{{ trigger.slots.title }}"
    response_variable: result
  - set_conversation_response: >-
      {% if result.requested %}Requested {{ result.title }} ({{ result.year }}).
      {% else %}{{ result.title }} is already {{ result.status | replace('_', ' ') }}.{% endif %}
```

## Development

```sh
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q -p no:logging

cd frontend && npm ci
npm test && npm run build   # rebuilds the committed card bundle
```
