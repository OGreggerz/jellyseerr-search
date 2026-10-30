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
*Add card → Jellyseerr Search*. Before you type it shows what's on a streaming
service (below), what's trending today, or what's popular (switch on the heading; follows the All / Movies / TV filter). Popular
TV leaves out shows with fewer than 500 TMDB votes, which are mostly daily news and soaps. Type a title, tap a poster, pick seasons for
shows, and tap **Request**. Posters show whether a title is already requested
or available.

```yaml
type: custom:jellyseerr-search-card
title: Request movies & TV
media_type: all      # default filter: all | movie | tv
show_4k: false       # offer a 4K toggle (needs 4K Radarr/Sonarr in Jellyseerr)
show_trending: true  # trending / popular / streaming titles while the search box is empty
show_remove: false   # a Remove button on titles you have; deletes the files (asks first)
services: [netflix, disney, crunchyroll]  # Streaming list's services, in order (default: all)
region: GB           # country whose streaming catalogues to show (default GB)
```

**Streaming.** What the card opens on (*Streaming / Trending / Popular* on the
heading): what your streaming services carry in your country. **All** (first, the
default) looks across every service the card offers; pick the
service, a genre and *Popular*, *Top rated* or *Newest*, and **Show more** adds
the next page (20 films and 20 shows when the filter is on All). Services: `netflix`, `disney`,
`crunchyroll`, `prime`, `apple`, `now`, `iplayer`, `itvx`, `channel4`,
`paramount`, `skygo`. On Disney+ a brand row narrows it to **Disney**, **Pixar**,
**Marvel**, **Star Wars** (Lucasfilm) or **Nat Geo**; Pixar, Star Wars and Nat Geo
are films only, because Seerr can filter TV by keyword or original network but not
by studio. The genre row starts with **Christmas** (TMDB's "christmas" keyword, so
it works with any service or brand). Availability is TMDB's (JustWatch) watch-provider data,
as Seerr shows it. Titles with few TMDB votes are left out: 500 for Popular and
Top rated (200 with a genre), 50 for Newest, so the month's releases still show;
50 for Christmas; none for a brand (20 for Top rated), whose lists are curated already.

If your dashboards are in YAML mode, add `/jellyseerr_search/jellyseerr-search-card.js`
as a JavaScript module resource yourself.

**Downloaded.** A fourth chip beside All / Movies / TV lists what the server
already has (available or partly available in Jellyseerr), newest first;
typing narrows it. Tap a title for the usual screen: Remove, or Episodes to get
more.

**Waiting (needs Sonarr and/or Radarr in the options).** A chip listing what
Sonarr and Radarr want but haven't got, each marked *Not out yet*, *Not found
yet* or *Downloading*, with the reason: a film's digital or physical release
date (or, for a cinema-only film, roughly when Radarr will count it as out: 90
days after the cinema date), a show's next episode, when it was last searched.
Sonarr and Radarr keep watching their indexers' new-release feeds by themselves (every 15 and 30 minutes by default) and grab what fits. **Check now** (and **Check all now**) runs the app's interactive search on demand (one indexer hit, grabs nothing)
and says whether suitable copies are out there, or why the ones found would be
turned down (e.g. a cinema recording). **Search again** asks the app to search
and grab. Every title's page also says whether it's out (TMDB's dates via
Jellyseerr: UK first, then US).

**Episode picker (optional, needs Sonarr).** Jellyseerr requests whole seasons
only. Add Sonarr's URL and API key under the integration's **Configure** button
and each season in the card gets an **Episodes** link to tick single episodes
and download them. **Get new episodes**, on the show's page, has future
episodes (and new seasons) download when they air; ticking it on a show Sonarr
doesn't have adds it. **Daily show** (programmes named by date, like quizzes and
soaps, which Sonarr can't match as a normal series) is set automatically: on
Download, Sonarr test-searches the latest aired pick; if nothing matches, the
other series type is tried and kept if it matches. That works from a show's
first episode, where air dates can't tell. If only future episodes are picked,
or Get new episodes is switched on, the show's latest aired episode is tested
instead. **Get new episodes** also covers episodes
listed very late (common for daily shows). Sonarr searches once for episodes
TVDB adds up to 14 days after they aired, but unmonitors ones added later; for
followed shows the integration monitors and searches those (aired since
following started, 2 hours after airing at the earliest, then every 6 hours for
14 days). Episodes you remove through the card are never fetched again. A
show's confirmed type is remembered, so the check runs once per show. There's no switch for Daily any more; if neither type can be tested
(nothing released yet) and it's wrong later, change it in Sonarr (the show →
Edit → Series Type). Episode lists come from Sonarr
(TVDB). The season list shows no episode counts: Jellyseerr's come from TMDB
and can be badly wrong for long-running shows. Sonarr only lists episodes of
shows it has, so opening the picker on a new show adds it to Sonarr with
nothing monitored; leaving the show without picking removes it again, and
anything still untouched after an hour is removed anyway (checked every 15
minutes, in case the card was closed instead). With `show_remove` on, downloaded episodes get a **Remove** button (asks first):
it deletes the file and unmonitors the episode so Sonarr doesn't fetch it
again; if that leaves nothing of the show, the show leaves Sonarr too.
These downloads aren't Jellyseerr requests: Jellyseerr shows
them as available once it syncs with Sonarr.

**Anime: English dub or Japanese with subtitles (needs Sonarr; Radarr for
films).** Works with three quality profiles on Sonarr and Radarr, found by
name: **Anime (English dub preferred)** (Japanese with subtitles now, replaced
by the dub when it's posted), **Anime (English dub only)** (waits for a dub)
and **Anime (Japanese + subtitles)**. Without all three, none of this shows.
An anime title's page (Seerr's anime keyword, or Japanese animation) gets an
**Audio** choice. Before Sonarr or Radarr has the title, it goes with Request,
Episodes or Get new episodes; with no choice, anime goes to Seerr's anime
profile, and anime films to "dub preferred" (Seerr itself has no anime routing
for films). Afterwards, changing it asks first, then moves the title to that
profile and, for a dub choice, searches for the episodes still in Japanese
(Sonarr and Radarr don't search after a profile change). The page says how many
downloaded episodes have English audio. Episodes, tiles and the Downloaded list
are labelled **Dub**, **Dual audio**, **Sub**, **Part dub** or **Sub only**,
from the audio tracks in the files themselves (Sonarr's and Radarr's media
info), not from release names. On "dub only", episodes not found are *Waiting
for dub*; shows that have every episode but some in Japanese appear in the
Waiting list as *Waiting for dub*, after everything else. **Check now** says
how many suitable copies have English audio; **Search again** includes the
Japanese episodes.

**Dub dates (optional).** With an [AnimeSchedule.net](https://animeschedule.net)
application token in the options, the page shows the next English dub episode
and when ("English dub: episode 3 Fri 30 Oct, 15:00 · dubbed up to episode 2"),
episodes show when their dub is expected (weekly from the next one), and the
Waiting list shows the next dub. The dub timetable for last week, this week and the next
three is read every six hours and matched to shows by name. Dates are credited
to AnimeSchedule.net, as its API terms require.

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
