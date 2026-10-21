# AGENTS.md

Home Assistant custom integration (`custom_components/jellyseerr_search/`) plus a
Lovelace search card. Searches movies/TV through **Jellyseerr** and requests
them (Jellyseerr → Radarr/Sonarr → download client). Mobile (the HA companion
app) is the primary target. Sibling project: Virtual Remote
(`../test_connection`, repo `kozelkevinr-create/virtual-remote`); conventions
here follow it. The user commits changes themselves.

## Architecture rules

- **One config entry = one Jellyseerr server.** `entry.runtime_data` is the
  `JellyseerrCoordinator`, which owns the `JellyseerrClient` and polls
  `/request/count` for the sensors.
- **Actions and WebSocket commands share one code path**:
  `services.resolve_client` / `async_search_media` / `async_trending_media` /
  `async_popular_media` / `async_request_media` / `async_remove_media` /
  `async_tv_seasons`. The card uses the WS commands (`jellyseerr_search/search`,
  `/trending`, `/popular`, `/seasons`, `/request`, `/remove`, `/version`); automations use the actions.
- Query strings are encoded like `encodeURIComponent` (`%20`, not `+`);
  Jellyseerr rejects anything else. A test pins this.
- Services, WS commands and card serving are registered in `async_setup`
  (once per process), never `async_setup_entry`.
- User-facing errors are `ServiceValidationError`/`HomeAssistantError` with a
  `translation_key`. Every key must exist in `strings.json`, and
  `translations/en.json` is a byte-identical copy. Tests enforce both.
- **Versions:** `manifest.json`, `frontend/package.json` and
  `const.CARD_VERSION` must match, and the bundle must be rebuilt after a bump.
  The card compares its version with `jellyseerr_search/version` to catch stale
  companion-app caches.

## Frontend

TypeScript + Lit + Vite, bundled to one file committed at
`custom_components/jellyseerr_search/frontend/jellyseerr-search-card.js`.
Lit uses `static properties` + `declare` fields, no decorators. The card
editor is `getConfigForm()` (HA-rendered), so no custom editor element. Pure
logic lives in `src/logic.ts` so vitest can cover it without a DOM.

```sh
cd frontend && npm ci
npm test && npm run build   # build = tsc --noEmit + vite, writes the bundle
```

## Testing

Python 3.13 (Homebrew; system Python is 3.9):

```sh
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q -p no:logging
```

`home-assistant-frontend` in `requirements_test.txt` must match the HA
version's `package_constraints.txt`, or every setup test fails.
