// <jellyseerr-search-card>: search Jellyseerr and request movies or shows.

import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { live } from "lit/directives/live.js";
import { errorMessage, toast, type HomeAssistant } from "./ha";
import {
  AUDIO_OPTIONS,
  Latest,
  airDateLabel,
  audioLines,
  audioSwitchWarning,
  episodeAudioLabel,
  episodeDubLine,
  canRequestMore,
  checkSummary,
  episodeLabel,
  filterLibrary,
  releaseLine,
  resultChips,
  waitingDetail,
  waitingLabel,
  isPickable,
  isRemovable,
  isRequestable,
  pickableEpisodes,
  requestableSeasons,
  statusLabel,
  STREAM_SORTS,
  appendNew,
  genresFor,
  servicesFor,
} from "./logic";
import type {
  AudioChoice,
  AudioState,
  Browse,
  CardConfig,
  Episode,
  MediaFilter,
  SearchResult,
  Season,
  SeasonEpisodes,
  CheckResult,
  ReleaseInfo,
  ShowState,
  SonarrShow,
  StreamSort,
  WaitingItem,
} from "./types";

export const CARD_VERSION = __CARD_VERSION__;
const DOMAIN = "jellyseerr_search";
const DEBOUNCE_MS = 400;
const MIN_QUERY = 2;
// A wall-mounted tablet keeps the card open for days; refetch the browse list after this.
const BROWSE_TTL_MS = 60 * 60 * 1000;
// Sonarr searches in the background and grabs 15-30 s after Download is pressed;
// refresh the episode list then so "Not found yet" turns into "Downloading".
const AFTER_DOWNLOAD_REFRESH_MS = [20_000, 60_000];

let versionChecked = false;
/** The server has Sonarr or Radarr set up, so the Waiting chip has something to show. */
let waitingAvailable = false;

const FILTERS: Array<{ value: MediaFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV" },
  { value: "downloaded", label: "Downloaded" },
  { value: "waiting", label: "Waiting" },
];

const BROWSE: Array<{ value: Browse; label: string; heading: string }> = [
  { value: "trending", label: "Trending", heading: "Trending today" },
  { value: "popular", label: "Popular", heading: "Popular" },
  // Not "On Netflix": the heading's length would change with the service, and on a
  // phone that moves the rows below it under the finger picking the next one.
  { value: "streaming", label: "Streaming", heading: "What's on" },
];
// TMDB's watch-provider data is per country; Mitchell's server is in the UK.
const DEFAULT_REGION = "GB";

/** Said when the server found the show's releases are (or aren't) named by date. */
function typeChangedMessage(title: string, type: string): string {
  return type === "daily"
    ? `${title} is released by date, so it's now set up as a daily show.`
    : `${title} isn't released by date, so it's no longer set up as a daily show.`;
}

export class JellyseerrSearchCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    _config: { state: true },
    _query: { state: true },
    _filter: { state: true },
    _results: { state: true },
    _browse: { state: true },
    _browseResults: { state: true },
    _browseError: { state: true },
    _service: { state: true },
    _genre: { state: true },
    _sort: { state: true },
    _browseMore: { state: true },
    _moreLoading: { state: true },
    _moreError: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _selected: { state: true },
    _seasons: { state: true },
    _seasonsError: { state: true },
    _chosen: { state: true },
    _is4k: { state: true },
    _requesting: { state: true },
    _confirmRemove: { state: true },
    _removing: { state: true },
    _staleVersion: { state: true },
    _picker: { state: true },
    _episodeSeason: { state: true },
    _episodes: { state: true },
    _episodesError: { state: true },
    _picked: { state: true },
    _pickerBusy: { state: true },
    _confirmRemoveEp: { state: true },
    _downloading: { state: true },
    _followBusy: { state: true },
    _show: { state: true },
    _waiting: { state: true },
    _release: { state: true },
    _seasonSource: { state: true },
    _waitingError: { state: true },
    _checks: { state: true },
    _waitingOn: { state: true },
    _checkingAll: { state: true },
    _library: { state: true },
    _libraryError: { state: true },
    _audio: { state: true },
    _audioPick: { state: true },
    _audioConfirm: { state: true },
    _audioBusy: { state: true },
  };

  declare hass: HomeAssistant;
  declare _config: CardConfig;
  declare _query: string;
  declare _filter: MediaFilter;
  declare _results?: SearchResult[];
  declare _browse: Browse;
  declare _browseResults?: SearchResult[];
  declare _browseError?: string;
  /** Streaming list: the service's SERVICES key, a GENRES key ("" = all) and the order. */
  declare _service: string;
  declare _genre: string;
  declare _sort: StreamSort;
  /** The Streaming list has another page; _moreLoading while it's fetched. */
  declare _browseMore: boolean;
  declare _moreLoading: boolean;
  declare _moreError?: string;
  declare _loading: boolean;
  declare _error?: string;
  declare _selected?: SearchResult;
  declare _seasons?: Season[];
  declare _seasonsError?: string;
  declare _chosen: Set<number>;
  declare _is4k: boolean;
  declare _requesting: boolean;
  declare _confirmRemove: boolean;
  declare _removing: boolean;
  declare _staleVersion?: string;
  /** Sonarr is set up, so seasons offer "Choose episodes". */
  declare _picker: boolean;
  /** The season whose episodes are open, if any. */
  declare _episodeSeason?: Season;
  declare _episodes?: SeasonEpisodes;
  declare _episodesError?: string;
  declare _picked: Set<number>;
  declare _pickerBusy: boolean;
  /** A downloaded episode whose Remove was tapped once: the next tap deletes. */
  declare _confirmRemoveEp?: number;
  /** Download pressed: the server may be test-searching to check the naming. */
  declare _downloading: boolean;
  /** Get new episodes tapped: the server may be test-searching first. */
  declare _followBusy: boolean;
  /** Sonarr's view of the open show (follow state), when Sonarr is set up. */
  declare _show?: ShowState | null;
  /** "sonarr" when the season list is Sonarr's (its numbering), so Request goes there. */
  declare _seasonSource?: string;
  /** TMDB's release dates for the open title ("Is it out?"). */
  declare _release?: ReleaseInfo;
  /** Wanted but not downloaded (Sonarr/Radarr), for the Waiting filter. */
  declare _waiting?: WaitingItem[];
  declare _waitingError?: string;
  /** Indexer check results (or "checking"), by `${media_type}/${arr_id}`. */
  declare _checks: Record<string, CheckResult | "checking" | string>;
  declare _waitingOn: boolean;
  declare _checkingAll: boolean;
  /** What the server already has, for the Downloaded filter. */
  declare _library?: SearchResult[];
  declare _libraryError?: string;
  /** The open title's audio section (anime: dub or sub), null if not available. */
  declare _audio?: AudioState | null;
  /** The audio chosen for a title Sonarr/Radarr hasn't got yet: goes with the request. */
  declare _audioPick: AudioChoice;
  /** A switch for a title Sonarr/Radarr has, waiting for "Switch". */
  declare _audioConfirm?: AudioChoice;
  declare _audioBusy: boolean;

  private _debounce?: ReturnType<typeof setTimeout>;
  private _latestSearch = new Latest();
  private _latestSeasons = new Latest();
  private _latestBrowse = new Latest();
  private _latestEpisodes = new Latest();
  private _latestLibrary = new Latest();
  /** A Sonarr series the picker added for the open show; removed again on leaving
   *  the show unless something was picked (Sonarr checks that too). */
  private _addedSeries?: number;
  private _refreshTimers: Array<ReturnType<typeof setTimeout>> = [];
  private _browseAt = 0;
  /** What _browseResults were loaded for (see _currentBrowseKey). */
  private _browseKey?: string;
  /** The Streaming page last loaded. */
  private _browsePage = 1;

  constructor() {
    super();
    this._query = "";
    this._filter = "all";
    this._browse = "trending";
    this._service = "";
    this._genre = "";
    this._sort = "popular";
    this._browseMore = false;
    this._moreLoading = false;
    this._loading = false;
    this._chosen = new Set();
    this._is4k = false;
    this._requesting = false;
    this._confirmRemove = false;
    this._removing = false;
    this._picker = false;
    this._picked = new Set();
    this._pickerBusy = false;
    this._downloading = false;
    this._followBusy = false;
    this._checks = {};
    this._waitingOn = waitingAvailable;
    this._checkingAll = false;
    this._audioPick = "dub";
    this._audioBusy = false;
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        {
          name: "media_type",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "all", label: "Movies and TV shows" },
                { value: "movie", label: "Movies" },
                { value: "tv", label: "TV shows" },
              ],
            },
          },
        },
        { name: "show_trending", selector: { boolean: {} } },
        {
          name: "services",
          selector: {
            select: {
              multiple: true,
              mode: "list",
              options: servicesFor().map((s) => ({ value: s.key, label: s.label })),
            },
          },
        },
        { name: "region", selector: { text: {} } },
        { name: "show_4k", selector: { boolean: {} } },
        { name: "show_remove", selector: { boolean: {} } },
        { name: "config_entry_id", selector: { config_entry: { integration: DOMAIN } } },
      ],
      computeLabel: (field: { name: string }) =>
        ({
          title: "Title",
          media_type: "Default filter",
          show_trending: "Show trending, popular and streaming titles before searching",
          services: "Streaming services to offer (none ticked = all)",
          region: "Streaming country, two letters (default GB)",
          show_4k: "Offer 4K requests",
          show_remove: "Offer Remove (deletes the files from Radarr/Sonarr)",
          config_entry_id: "Jellyseerr server (only if you have several)",
        })[field.name],
    };
  }

  static getStubConfig(): Partial<CardConfig> {
    return { title: "Request movies & TV" };
  }

  setConfig(config: CardConfig): void {
    if (!config) throw new Error("Invalid configuration");
    if (config.media_type && !FILTERS.some((f) => f.value === config.media_type)) {
      throw new Error("media_type must be all, movie or tv");
    }
    this._config = config;
    this._filter = config.media_type ?? "all";
  }

  getCardSize(): number {
    return this._results?.length || (this._showBrowse() && this._browseResults?.length) ? 8 : 2;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    clearTimeout(this._debounce);
    this._clearRefreshTimers();
  }

  protected override updated(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass && !versionChecked) {
      versionChecked = true;
      void this._checkVersion();
    }
    if (changed.has("hass") && this.hass && this._browseDue()) void this._loadBrowse();
  }

  /** A cached old card talking to a newer backend: offer a cache-clearing reload. */
  private async _checkVersion(): Promise<void> {
    try {
      const { version, waiting } = await this.hass.callWS<{ version: string; waiting?: boolean }>({
        type: `${DOMAIN}/version`,
      });
      if (version !== CARD_VERSION) this._staleVersion = version;
      waitingAvailable = !!waiting;
      this._waitingOn = waitingAvailable;
    } catch {
      // Integration not loaded; searches will report that themselves.
    }
  }

  private async _reload(): Promise<void> {
    try {
      if ("caches" in window) {
        for (const key of await caches.keys()) await caches.delete(key);
      }
    } finally {
      location.reload();
    }
  }

  private _entry(): Record<string, string> {
    return this._config.config_entry_id ? { config_entry_id: this._config.config_entry_id } : {};
  }

  // --- waiting ------------------------------------------------------------

  private async _loadWaiting(): Promise<void> {
    this._waitingError = undefined;
    try {
      const { results } = await this.hass.callWS<{ results: WaitingItem[] }>({
        type: `${DOMAIN}/waiting`,
        ...this._entry(),
      });
      if (this._filter === "waiting") this._waiting = results;
    } catch (err) {
      if (this._filter === "waiting") this._waitingError = errorMessage(err);
    }
  }

  private _key(item: WaitingItem): string {
    return `${item.media_type}/${item.arr_id}`;
  }

  /** Is a copy out there? One indexer search; grabs nothing. */
  private async _checkWaiting(item: WaitingItem): Promise<void> {
    const key = this._key(item);
    this._checks = { ...this._checks, [key]: "checking" };
    try {
      const result = await this.hass.callWS<CheckResult>({
        type: `${DOMAIN}/waiting/check`,
        media_type: item.media_type,
        arr_id: item.arr_id,
        ...this._entry(),
      });
      this._checks = { ...this._checks, [key]: result };
    } catch (err) {
      this._checks = { ...this._checks, [key]: `Check failed: ${errorMessage(err)}` };
    }
  }

  /** Check every title not already downloading, one after another (each is an
   *  indexer search, so not all at once). */
  private async _checkAll(items: WaitingItem[]): Promise<void> {
    if (this._checkingAll) return;
    this._checkingAll = true;
    try {
      for (const item of items) {
        if (this._filter !== "waiting") break;
        await this._checkWaiting(item);
      }
    } finally {
      this._checkingAll = false;
    }
  }

  private async _searchWaiting(item: WaitingItem): Promise<void> {
    try {
      await this.hass.callWS({
        type: `${DOMAIN}/waiting/search`,
        media_type: item.media_type,
        arr_id: item.arr_id,
        ...this._entry(),
      });
      toast(this, `Searching for ${item.title} now. It downloads by itself if a suitable copy turns up.`);
      setTimeout(() => {
        if (this._filter === "waiting" && !this._selected) void this._loadWaiting();
      }, 30_000);
    } catch (err) {
      toast(this, `Search failed: ${errorMessage(err)}`);
    }
  }

  private _openWaiting(item: WaitingItem): void {
    if (!item.tmdb_id) return;
    this._open({
      tmdb_id: item.tmdb_id,
      media_type: item.media_type,
      title: item.title,
      year: item.year,
      overview: "",
      poster_url: item.poster_url,
      status: "processing",
    });
  }

  // --- trending / popular -------------------------------------------------

  private _showBrowse(): boolean {
    return (
      this._filter !== "downloaded" &&
      this._filter !== "waiting" &&
      this._config.show_trending !== false &&
      this._query.trim().length < MIN_QUERY
    );
  }

  // --- downloaded ---------------------------------------------------------

  private async _loadLibrary(): Promise<void> {
    const current = this._latestLibrary.next();
    this._libraryError = undefined;
    try {
      const { results } = await this.hass.callWS<{ results: SearchResult[] }>({
        type: `${DOMAIN}/library`,
        ...this._entry(),
      });
      if (current()) this._library = results;
    } catch (err) {
      if (current()) this._libraryError = errorMessage(err);
    }
  }

  /** Missing, for another list or filter, or older than the TTL, and on screen. */
  private _browseDue(): boolean {
    if (!this._showBrowse() || this._selected) return false;
    if (this._browseKey !== this._currentBrowseKey()) return true;
    return Date.now() - this._browseAt > BROWSE_TTL_MS;
  }

  /** What the browse list on screen should be: list, filter and, for Streaming, its choices. */
  private _currentBrowseKey(): string {
    const key = `${this._browse}/${this._filter}`;
    return this._browse === "streaming" ? `${key}/${this._streamService().key}/${this._genre}/${this._sort}` : key;
  }

  private _streamService() {
    const services = servicesFor(this._config.services);
    return services.find((s) => s.key === this._service) ?? services[0];
  }

  /** The discover command for one page of the Streaming list. */
  private _discoverMessage(page: number) {
    return {
      type: `${DOMAIN}/discover`,
      provider: this._streamService().id,
      region: (this._config.region || DEFAULT_REGION).toUpperCase(),
      media_type: this._filter,
      sort: this._sort,
      ...(this._genre ? { genre: this._genre } : {}),
      page,
      ...this._entry(),
    };
  }

  private async _loadBrowse(): Promise<void> {
    const current = this._latestBrowse.next();
    const key = this._currentBrowseKey();
    if (this._browseKey !== key) this._browseResults = undefined;
    // Set before the call so the frequent hass updates don't refetch meanwhile.
    this._browseKey = key;
    this._browseAt = Date.now();
    this._browseError = undefined;
    this._moreError = undefined;
    this._browseMore = false;
    try {
      if (this._browse === "streaming") {
        const found = await this.hass.callWS<{ results: SearchResult[]; has_more: boolean }>(
          this._discoverMessage(1),
        );
        if (!current()) return;
        this._browsePage = 1;
        this._browseResults = found.results;
        this._browseMore = found.has_more;
        return;
      }
      const { results } = await this.hass.callWS<{ results: SearchResult[] }>({
        type: `${DOMAIN}/${this._browse}`,
        media_type: this._filter,
        ...this._entry(),
      });
      if (current()) this._browseResults = results;
    } catch (err) {
      if (current()) this._browseError = errorMessage(err);
    }
  }

  /** Show more: the Streaming list's next page, added below. */
  private async _loadMore(): Promise<void> {
    if (this._moreLoading || !this._browseResults) return;
    const key = this._browseKey;
    const page = this._browsePage + 1;
    this._moreLoading = true;
    this._moreError = undefined;
    try {
      const found = await this.hass.callWS<{ results: SearchResult[]; has_more: boolean }>(
        this._discoverMessage(page),
      );
      // Another service, genre or filter was picked meanwhile: this page is for the old list.
      if (key !== this._browseKey || !this._browseResults) return;
      this._browsePage = page;
      this._browseResults = appendNew(this._browseResults, found.results);
      this._browseMore = found.has_more;
    } catch (err) {
      if (key === this._browseKey) this._moreError = errorMessage(err);
    } finally {
      this._moreLoading = false;
    }
  }

  private _setBrowse(browse: Browse): void {
    if (browse === this._browse) return;
    this._browse = browse;
    if (this._browseDue()) void this._loadBrowse();
  }

  private _setStream(change: { service?: string; genre?: string; sort?: StreamSort }): void {
    if (change.service !== undefined) this._service = change.service;
    if (change.genre !== undefined) this._genre = change.genre;
    if (change.sort !== undefined) this._sort = change.sort;
    if (this._browseDue()) void this._loadBrowse();
  }

  // --- search -------------------------------------------------------------

  private _onInput(ev: InputEvent): void {
    this._query = (ev.target as HTMLInputElement).value;
    clearTimeout(this._debounce);
    if (this._filter === "downloaded" || this._filter === "waiting") return; // Narrows the list; nothing to fetch.
    this._debounce = setTimeout(() => void this._search(), DEBOUNCE_MS);
  }

  private _onKeydown(ev: KeyboardEvent): void {
    if (ev.key !== "Enter") return;
    clearTimeout(this._debounce);
    (ev.target as HTMLInputElement).blur(); // Drops the phone keyboard so results are visible.
    void this._search();
  }

  private _clear(): void {
    this._leaveShow();
    clearTimeout(this._debounce);
    this._latestSearch.next(); // Anything in flight is now stale.
    this._query = "";
    this._results = undefined;
    this._error = undefined;
    this._loading = false;
    this._selected = undefined;
  }

  private _setFilter(filter: MediaFilter): void {
    if (filter === this._filter) return;
    this._filter = filter;
    // Horror has no TV genre (nor Reality a film one): drop a genre the new filter lacks.
    if (this._genre && !genresFor(filter).some((g) => g.key === this._genre)) this._genre = "";
    if (filter === "downloaded") void this._loadLibrary();
    else if (filter === "waiting") void this._loadWaiting();
    else if (this._query.trim().length >= MIN_QUERY) void this._search();
    else if (this._browseDue()) void this._loadBrowse();
  }

  private async _search(): Promise<void> {
    if (this._filter === "downloaded" || this._filter === "waiting") return;
    const query = this._query.trim();
    if (query.length < MIN_QUERY) {
      this._latestSearch.next();
      this._results = undefined;
      this._loading = false;
      return;
    }
    const current = this._latestSearch.next();
    this._loading = true;
    this._error = undefined;
    try {
      const { results } = await this.hass.callWS<{ results: SearchResult[] }>({
        type: `${DOMAIN}/search`,
        query,
        media_type: this._filter,
        ...this._entry(),
      });
      if (!current()) return;
      this._results = results;
      this._selected = undefined;
    } catch (err) {
      if (current()) this._error = errorMessage(err);
    } finally {
      if (current()) this._loading = false;
    }
  }

  // --- detail + request ---------------------------------------------------

  private _open(result: SearchResult): void {
    this._leaveShow();
    this._selected = result;
    this._seasons = undefined;
    this._seasonsError = undefined;
    this._chosen = new Set();
    this._is4k = false;
    this._confirmRemove = false;
    this._picker = false;
    this._show = undefined;
    this._release = undefined;
    this._seasonSource = undefined;
    this._audio = undefined;
    this._audioPick = "dub";
    this._audioConfirm = undefined;
    this._closeEpisodes();
    void this._loadRelease(result);
    void this._loadAudio(result);
    if (result.media_type === "tv") void this._loadSeasons(result.tmdb_id);
  }

  private async _loadRelease(item: SearchResult): Promise<void> {
    try {
      const info = await this.hass.callWS<ReleaseInfo>({
        type: `${DOMAIN}/release`,
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
        ...this._entry(),
      });
      if (this._selected === item) this._release = info;
    } catch {
      // Older integration or Jellyseerr hiccup: just no line.
    }
  }

  private async _loadAudio(item: SearchResult): Promise<void> {
    try {
      const state = await this.hass.callWS<AudioState | null>({
        type: `${DOMAIN}/audio`,
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
        ...this._entry(),
      });
      if (this._selected?.tmdb_id === item.tmdb_id && this._selected.media_type === item.media_type) this._audio = state;
    } catch {
      // Older integration, or Sonarr/Radarr down: no audio section.
      if (this._selected === item) this._audio = null;
    }
  }

  /** The audio to send with a request or an add: only for anime that isn't in
   *  Sonarr/Radarr yet (once it is, its profile says). */
  private _audioFor(): { audio?: AudioChoice } {
    const a = this._audio;
    return a && a.available && a.anime && !a.in_arr ? { audio: this._audioPick } : {};
  }

  private async _switchAudio(to: AudioChoice): Promise<void> {
    const item = this._selected;
    if (!item || this._audioBusy) return;
    this._audioBusy = true;
    try {
      const state = await this.hass.callWS<AudioState>({
        type: `${DOMAIN}/audio`,
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
        audio: to,
        ...this._entry(),
      });
      const label = AUDIO_OPTIONS.find((o) => o.value === to)?.label ?? to;
      toast(this, `${item.title}: ${label.toLowerCase()}.${to !== "sub" && state.dub_wanted ? " Searching for dubs now." : ""}`);
      if (this._selected !== item) return;
      this._audio = state;
      this._audioConfirm = undefined;
      if (this._episodes && this._episodeSeason) void this._loadEpisodes(item.tmdb_id, this._episodeSeason.season_number);
    } catch (err) {
      toast(this, `Couldn't change it: ${errorMessage(err)}`);
    } finally {
      this._audioBusy = false;
    }
  }

  private async _loadSeasons(tmdbId: number): Promise<void> {
    const current = this._latestSeasons.next();
    try {
      const { seasons, episode_picker, show, season_source } = await this.hass.callWS<{
        seasons: Season[];
        episode_picker?: boolean;
        show?: ShowState | null;
        season_source?: string;
      }>({
        type: `${DOMAIN}/seasons`,
        tmdb_id: tmdbId,
        ...this._entry(),
      });
      if (!current()) return;
      this._seasons = seasons;
      this._picker = !!episode_picker;
      this._show = show;
      this._seasonSource = season_source;
      // Requests through Sonarr download straight away: nothing pre-ticked.
      this._chosen = season_source === "sonarr" ? new Set() : new Set(requestableSeasons(seasons));
    } catch (err) {
      if (current()) this._seasonsError = errorMessage(err);
    }
  }

  private _toggleSeason(n: number): void {
    const chosen = new Set(this._chosen);
    chosen.has(n) ? chosen.delete(n) : chosen.add(n);
    this._chosen = chosen;
  }

  private _toggleAllSeasons(): void {
    const all = requestableSeasons(this._seasons ?? []);
    this._chosen = this._chosen.size === all.length ? new Set() : new Set(all);
  }

  private async _request(): Promise<void> {
    const item = this._selected;
    if (!item || this._requesting) return;
    if (item.media_type === "tv" && this._seasonSource === "sonarr" && this._seasons) {
      await this._requestThroughSonarr(item);
      return;
    }
    const msg: Record<string, unknown> = {
      type: `${DOMAIN}/request`,
      tmdb_id: item.tmdb_id,
      media_type: item.media_type,
      is_4k: this._is4k,
      ...this._audioFor(),
      ...this._entry(),
    };
    if (item.media_type === "tv") {
      // Without a season list (lookup failed) fall back to asking for everything.
      msg.seasons = this._seasons ? [...this._chosen].sort((a, b) => a - b) : "all";
    }
    this._requesting = true;
    try {
      await this.hass.callWS(msg);
      toast(this, `Requested ${item.title}`);
      this._markRequested(item);
      void this._loadAudio(item);
    } catch (err) {
      toast(this, `Request failed: ${errorMessage(err)}`);
    } finally {
      this._requesting = false;
    }
  }

  /** Seasons in Sonarr's numbering go to Sonarr: it monitors and searches them. */
  private async _requestThroughSonarr(item: SearchResult): Promise<void> {
    const seasons = [...this._chosen].sort((a, b) => a - b);
    if (!seasons.length) return;
    this._requesting = true;
    try {
      const result = await this.hass.callWS<{ series_type_changed?: string | null }>({
        type: `${DOMAIN}/episodes/request`,
        tmdb_id: item.tmdb_id,
        seasons,
        ...this._audioFor(),
        ...this._entry(),
      });
      const changed = result.series_type_changed ? ` ${typeChangedMessage(item.title, result.series_type_changed)}` : "";
      const which = seasons.length === 1 ? `series ${seasons[0]}` : `series ${seasons.join(", ")}`;
      toast(this, `Getting ${which} of ${item.title}.${changed}`);
      if (this._addedSeries !== undefined) this._addedSeries = undefined;
      if (this._selected === item) {
        void this._loadSeasons(item.tmdb_id);
        void this._loadAudio(item);
      }
    } catch (err) {
      toast(this, `Request failed: ${errorMessage(err)}`);
    } finally {
      this._requesting = false;
    }
  }

  /** First tap arms the button; the second, on "Delete files", removes. */
  private async _remove(): Promise<void> {
    const item = this._selected;
    if (!item || this._removing) return;
    if (!this._confirmRemove) {
      this._confirmRemove = true;
      return;
    }
    this._removing = true;
    try {
      await this.hass.callWS({
        type: `${DOMAIN}/remove`,
        tmdb_id: item.tmdb_id,
        media_type: item.media_type,
        ...this._entry(),
      });
      toast(this, `Removed ${item.title}`);
      this._setStatus(item, "deleted");
      this._library = this._library?.filter((r) => !(r.tmdb_id === item.tmdb_id && r.media_type === item.media_type));
    } catch (err) {
      toast(this, `Remove failed: ${errorMessage(err)}`);
    } finally {
      this._removing = false;
      this._confirmRemove = false;
    }
  }

  private _setStatus(item: SearchResult, status: SearchResult["status"]): void {
    const updated = { ...item, status };
    const swap = (list?: SearchResult[]) =>
      list?.map((r) => (r.tmdb_id === item.tmdb_id && r.media_type === item.media_type ? updated : r));
    this._results = swap(this._results);
    this._browseResults = swap(this._browseResults);
    if (this._selected === item) this._selected = updated;
    if (this._seasons && status === "deleted") {
      this._seasons = this._seasons.map((s) => ({ ...s, status: "deleted" }));
    }
  }

  /** Show the new state right away instead of waiting for a re-search. */
  private _markRequested(item: SearchResult): void {
    const status = item.status === "partially_available" ? item.status : "pending";
    const updated = { ...item, status } as SearchResult;
    const swap = (list?: SearchResult[]) =>
      list?.map((r) => (r.tmdb_id === item.tmdb_id && r.media_type === item.media_type ? updated : r));
    this._results = swap(this._results);
    this._browseResults = swap(this._browseResults);
    if (this._selected === item) this._selected = updated;
    if (this._seasons) {
      this._seasons = this._seasons.map((s) =>
        this._chosen.has(s.season_number) ? { ...s, status: "pending" } : s,
      );
      this._chosen = new Set();
    }
  }

  // --- episode picker (Sonarr) --------------------------------------------

  private _openEpisodes(season: Season, ev: Event): void {
    ev.preventDefault();
    ev.stopPropagation();
    if (!this._selected) return;
    this._episodeSeason = season;
    this._episodes = undefined;
    this._episodesError = undefined;
    this._picked = new Set();
    void this._loadEpisodes(this._selected.tmdb_id, season.season_number);
  }

  private async _loadEpisodes(tmdbId: number, seasonNumber: number): Promise<void> {
    const current = this._latestEpisodes.next();
    try {
      const result = await this.hass.callWS<SeasonEpisodes>({
        type: `${DOMAIN}/episodes`,
        tmdb_id: tmdbId,
        season_number: seasonNumber,
        ...this._audioFor(),
        ...this._entry(),
      });
      if (!current()) return; // A stale add is left to the server's sweep.
      if (result.added) {
        this._addedSeries = result.series_id;
        if (this._selected) void this._loadAudio(this._selected); // Now in Sonarr, on its profile.
      }
      this._episodes = result;
    } catch (err) {
      if (current()) this._episodesError = errorMessage(err);
    }
  }

  private _clearRefreshTimers(): void {
    this._refreshTimers.forEach(clearTimeout);
    this._refreshTimers = [];
  }

  private _closeEpisodes(): void {
    this._confirmRemoveEp = undefined;
    this._clearRefreshTimers();
    this._latestEpisodes.next();
    this._episodeSeason = undefined;
    this._episodes = undefined;
    this._episodesError = undefined;
    this._picked = new Set();
  }

  /** Leaving a show: drop a Sonarr series the picker added if nothing was picked. */
  private _leaveShow(): void {
    const seriesId = this._addedSeries;
    this._addedSeries = undefined;
    if (seriesId === undefined || !this.hass) return;
    this.hass
      .callWS({ type: `${DOMAIN}/episodes/discard`, series_id: seriesId, ...this._entry() })
      .catch(() => undefined); // Left in Sonarr, unmonitored: harmless.
  }

  private _back(): void {
    this._leaveShow();
    this._closeEpisodes();
    this._selected = undefined;
    // Something may have been removed or downloaded meanwhile.
    if (this._filter === "downloaded") void this._loadLibrary();
    if (this._filter === "waiting") void this._loadWaiting();
  }

  private _togglePick(id: number): void {
    const picked = new Set(this._picked);
    picked.has(id) ? picked.delete(id) : picked.add(id);
    this._picked = picked;
  }

  private _toggleAllPicks(): void {
    const all = pickableEpisodes(this._episodes?.episodes ?? []);
    this._picked = this._picked.size === all.length ? new Set() : new Set(all);
  }

  /** Still on the show and season an action started on? (Actions can take
   *  minutes: the naming check waits for the indexers.) */
  private _stillOn(item: SearchResult, seriesId: number): boolean {
    return this._selected === item && this._episodes?.series_id === seriesId;
  }

  /** The show was removed from Sonarr while open (the sweep, another user, or by
   *  hand): reopening its episodes adds it back. */
  private _recoverIfGone(err: unknown, item: SearchResult, seasonNumber: number): boolean {
    if ((err as { translation_key?: string } | null)?.translation_key !== "series_gone") return false;
    toast(this, `${item.title} had been tidied out of Sonarr. It's back now: try again.`);
    if (this._selected === item) void this._loadEpisodes(item.tmdb_id, seasonNumber);
    return true;
  }

  private async _download(): Promise<void> {
    const list = this._episodes;
    const item = this._selected;
    if (!list || !item || !this._picked.size || this._pickerBusy) return;
    const ids = [...this._picked];
    this._pickerBusy = true;
    this._downloading = true;
    try {
      const result = await this.hass.callWS<SonarrShow & { series_type_changed: string | null }>({
        type: `${DOMAIN}/episodes/download`,
        series_id: list.series_id,
        episode_ids: ids,
        ...this._entry(),
      });
      if (this._addedSeries === list.series_id) this._addedSeries = undefined; // Picked: keep the show.
      const changed = result.series_type_changed ? ` ${typeChangedMessage(list.title, result.series_type_changed)}` : "";
      toast(this, `Downloading ${ids.length} episode${ids.length === 1 ? "" : "s"} of ${list.title}.${changed}`);
      if (!this._stillOn(item, list.series_id)) return; // Moved on meanwhile; Sonarr has it.
      this._picked = new Set();
      await this._loadEpisodes(item.tmdb_id, list.season_number);
      this._clearRefreshTimers();
      this._refreshTimers = AFTER_DOWNLOAD_REFRESH_MS.map((ms) =>
        setTimeout(() => {
          if (this._stillOn(item, list.series_id)) void this._loadEpisodes(item.tmdb_id, list.season_number);
        }, ms),
      );
    } catch (err) {
      if (!this._recoverIfGone(err, item, list.season_number)) toast(this, `Download failed: ${errorMessage(err)}`);
    } finally {
      this._pickerBusy = false;
      this._downloading = false;
    }
  }

  private _askRemoveEpisode(id: number, ev: Event): void {
    ev.preventDefault();
    ev.stopPropagation();
    this._confirmRemoveEp = id;
  }

  private async _removeEpisode(ep: Episode): Promise<void> {
    const list = this._episodes;
    const item = this._selected;
    if (!list || !item || this._pickerBusy) return;
    this._pickerBusy = true;
    try {
      const result = await this.hass.callWS<{ show_removed: boolean }>({
        type: `${DOMAIN}/episodes/remove`,
        series_id: list.series_id,
        tmdb_id: item.tmdb_id,
        episode_ids: [ep.id],
        ...this._entry(),
      });
      this._confirmRemoveEp = undefined;
      // Jellyseerr has forgotten a show with nothing left: show that now.
      if (result.show_removed) {
        toast(this, `Removed episode ${ep.episode_number}. Nothing else was left, so ${list.title} is gone.`);
        if (this._addedSeries === list.series_id) this._addedSeries = undefined;
        this._library = this._library?.filter((r) => !(r.tmdb_id === item.tmdb_id && r.media_type === item.media_type));
        this._setStatus(item, "not_requested");
        if (this._stillOn(item, list.series_id)) {
          this._closeEpisodes();
          void this._loadSeasons(item.tmdb_id);
        }
      } else {
        toast(this, `Removed episode ${ep.episode_number} of ${list.title}`);
        if (this._stillOn(item, list.series_id)) await this._loadEpisodes(item.tmdb_id, list.season_number);
      }
    } catch (err) {
      if (!this._recoverIfGone(err, item, list.season_number)) toast(this, `Remove failed: ${errorMessage(err)}`);
    } finally {
      this._pickerBusy = false;
    }
  }

  /** Get new episodes, from the show page. The server adds the show to Sonarr
   *  if it hasn't got it, checks how it's released, then follows it. */
  private async _setFollowShow(value: boolean): Promise<void> {
    const item = this._selected;
    if (!item || this._followBusy) return;
    this._followBusy = true;
    try {
      const show = await this.hass.callWS<ShowState & { title?: string; series_type_changed?: string | null }>({
        type: `${DOMAIN}/episodes/follow`,
        tmdb_id: item.tmdb_id,
        follow_new: value,
        ...this._audioFor(),
        ...this._entry(),
      });
      if (show.series_type_changed) toast(this, typeChangedMessage(item.title, show.series_type_changed));
      if (value && !show.follow_new) toast(this, `${item.title} has no regular series to follow yet.`);
      else if (value) toast(this, `New episodes of ${item.title} will download as they come out.`);
      if (this._selected !== item) return;
      this._show = { in_sonarr: show.in_sonarr, follow_new: show.follow_new };
      if (show.in_sonarr && !this._audio?.in_arr) void this._loadAudio(item);
      // Following changes which future episodes are monitored: refresh an open list.
      if (this._episodes && this._episodeSeason) void this._loadEpisodes(item.tmdb_id, this._episodeSeason.season_number);
    } catch (err) {
      toast(this, `Couldn't change it: ${errorMessage(err)}`);
      this.requestUpdate(); // The box must show what Sonarr has, not what was tapped.
    } finally {
      this._followBusy = false;
    }
  }

  /** Anime only: English dub or Japanese with subtitles, what's downloaded in
   *  English, and the next dub date. Before Sonarr/Radarr has the title the
   *  choice goes with the request; after, changing it asks first. */
  private _renderAudio(item: SearchResult) {
    const a = this._audio;
    if (!a || !a.available || !a.anime) return nothing;
    const current = a.in_arr ? a.audio : this._audioPick;
    const lines = audioLines(a, item.media_type);
    return html`
      <div class="seasons options audio" role="radiogroup" aria-label="Audio">
        <div class="seasons-head"><span>Audio</span></div>
        ${a.in_arr && !a.audio
          ? html`<div class="hint audio-note">
              On a profile that doesn't prefer English dubs. Pick one to set it.
            </div>`
          : nothing}
        ${AUDIO_OPTIONS.map(
          (o) => html`<label class="row option">
            <input
              type="radio"
              name="audio"
              .checked=${live((this._audioConfirm ?? current) === o.value)}
              ?disabled=${this._audioBusy}
              @change=${() => {
                if (a.in_arr) this._audioConfirm = o.value === a.audio ? undefined : o.value;
                else this._audioPick = o.value;
              }}
            />
            <span class="grow">${o.label}<span class="hint">${o.hint}</span></span>
          </label>`,
        )}
        ${this._audioConfirm
          ? html`<div class="confirm notice" role="alert">${audioSwitchWarning(this._audioConfirm, item.media_type)}</div>
              <div class="confirm-row">
                <button class="secondary" ?disabled=${this._audioBusy} @click=${() => (this._audioConfirm = undefined)}>
                  Cancel
                </button>
                <button class="primary" ?disabled=${this._audioBusy} @click=${() => this._switchAudio(this._audioConfirm!)}>
                  ${this._audioBusy ? "Switching…" : "Switch"}
                </button>
              </div>`
          : nothing}
        ${lines.map((l) => html`<div class="hint audio-line">${l}</div>`)}
        ${a.dub ? html`<div class="hint credit">Dub dates from <a href=${a.dub.url} target="_blank" rel="noreferrer">AnimeSchedule.net</a></div>` : nothing}
      </div>
    `;
  }

  private _renderFollow(item: SearchResult) {
    if (!this._picker || this._show === undefined) return nothing;
    if (this._show === null) return html`<div class="message">Couldn't reach Sonarr for this show.</div>`;
    return html`
      <div class="seasons options">
        <label class="row option">
          <input
            type="checkbox"
            .checked=${live(this._show.follow_new)}
            ?disabled=${this._followBusy || this._requesting}
            @change=${(e: Event) => this._setFollowShow((e.target as HTMLInputElement).checked)}
          />
          <span class="grow">
            Get new episodes
            ${this._followBusy
              ? html`<span class="hint busy">Checking how it's released and setting it up… This can take a
                  minute; it carries on if you leave.</span>`
              : html`<span class="hint">
                  Download new episodes of ${item.title} as they come out, including new series. Episodes already
                  out aren't fetched: tick their series below and Request. Turning it off also cancels upcoming
                  episodes you picked.
                </span>`}
          </span>
        </label>
      </div>
    `;
  }

  // --- render -------------------------------------------------------------

  protected override render() {
    if (!this._config) return nothing;
    return html`
      <ha-card .header=${this._config.title || undefined}>
        ${this._staleVersion
          ? html`<div class="stale">
              Card is out of date (server has ${this._staleVersion}).
              <button class="link" @click=${this._reload}>Reload</button>
            </div>`
          : nothing}
        ${this._selected && this._episodeSeason
          ? this._renderEpisodes(this._selected, this._episodeSeason)
          : this._selected
            ? this._renderDetail(this._selected)
            : this._renderSearch()}
      </ha-card>
    `;
  }

  private _renderSearch() {
    return html`
      <div class="search">
        <div class="field">
          <ha-icon icon="mdi:magnify"></ha-icon>
          <input
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            placeholder="Search movies and TV"
            aria-label="Search movies and TV"
            .value=${this._query}
            @input=${this._onInput}
            @keydown=${this._onKeydown}
          />
          ${this._query
            ? html`<button class="icon" aria-label="Clear" @click=${this._clear}>
                <ha-icon icon="mdi:close"></ha-icon>
              </button>`
            : nothing}
        </div>
        <div class="chips" role="radiogroup" aria-label="Media type">
          ${FILTERS.filter((f) => f.value !== "waiting" || this._waitingOn).map(
            (f) => html`<button
              class="chip ${f.value === this._filter ? "on" : ""}"
              role="radio"
              aria-checked=${f.value === this._filter}
              @click=${() => this._setFilter(f.value)}
            >
              ${f.label}
            </button>`,
          )}
        </div>
      </div>
      ${this._renderResults()}
    `;
  }

  private _renderResults() {
    if (this._filter === "downloaded") return this._renderLibrary();
    if (this._filter === "waiting") return this._renderWaiting();
    if (this._showBrowse()) return this._renderBrowse();
    if (this._error) return html`<div class="message error">${this._error}</div>`;
    if (this._loading && !this._results) return html`<div class="message">Searching…</div>`;
    if (!this._results) return nothing;
    if (!this._results.length) return html`<div class="message">No movies or shows found.</div>`;
    return html`
      <div class="grid ${this._loading ? "busy" : ""}">
        ${this._results.map((r) => this._renderTile(r))}
      </div>
    `;
  }

  private _renderBrowse() {
    const streaming = this._browse === "streaming";
    const heading = BROWSE.find((b) => b.value === this._browse)!.heading;
    let body;
    if (this._browseError) {
      body = html`<div class="message error">Couldn't load ${heading.toLowerCase()} (${this._browseError}).</div>`;
    } else if (!this._browseResults) {
      body = html`<div class="message">Loading…</div>`;
    } else if (!this._browseResults.length) {
      body = html`<div class="message">Nothing to show.</div>`;
    } else {
      body = html`<div class="grid">${this._browseResults.map((r) => this._renderTile(r))}</div>`;
    }
    return html`
      <div class="section browse">
        <span class="heading">${heading}</span>
        <div class="chips small" role="radiogroup" aria-label="Browse">
          ${BROWSE.map(
            (b) => html`<button
              class="chip ${b.value === this._browse ? "on" : ""}"
              role="radio"
              aria-checked=${b.value === this._browse}
              @click=${() => this._setBrowse(b.value)}
            >
              ${b.label}
            </button>`,
          )}
        </div>
      </div>
      ${streaming ? this._renderStreamPickers() : nothing} ${body}
      ${streaming
        ? html`${this._renderMore()}
            <div class="attribution">Streaming availability from JustWatch</div>`
        : nothing}
    `;
  }

  /** Service, genre and order for the Streaming list. Rows scroll sideways on a phone. */
  private _renderStreamPickers() {
    const service = this._streamService().key;
    const chip = (label: string, on: boolean, pick: () => void) =>
      html`<button class="chip ${on ? "on" : ""}" role="radio" aria-checked=${on} @click=${pick}>${label}</button>`;
    return html`
      <div class="chips scroll" role="radiogroup" aria-label="Streaming service">
        ${servicesFor(this._config.services).map((s) =>
          chip(s.label, s.key === service, () => this._setStream({ service: s.key })),
        )}
      </div>
      <div class="chips scroll small" role="radiogroup" aria-label="Genre">
        ${chip("All genres", !this._genre, () => this._setStream({ genre: "" }))}
        ${genresFor(this._filter).map((g) =>
          chip(g.label, g.key === this._genre, () => this._setStream({ genre: g.key })),
        )}
      </div>
      <div class="chips scroll small" role="radiogroup" aria-label="Order">
        ${STREAM_SORTS.map((s) => chip(s.label, s.value === this._sort, () => this._setStream({ sort: s.value })))}
      </div>
    `;
  }

  private _renderMore() {
    if (this._moreError) {
      return html`<div class="message error">
        Couldn't load more (${this._moreError}). <button class="link" @click=${this._loadMore}>Try again</button>
      </div>`;
    }
    if (!this._browseMore || !this._browseResults?.length) return nothing;
    return html`<div class="more">
      <button class="chip" ?disabled=${this._moreLoading} @click=${this._loadMore}>
        ${this._moreLoading ? "Loading…" : "Show more"}
      </button>
    </div>`;
  }

  private _renderLibrary() {
    let body;
    if (this._libraryError) {
      body = html`<div class="message error">Couldn't load what's downloaded (${this._libraryError}).</div>`;
    } else if (!this._library) {
      body = html`<div class="message">Loading…</div>`;
    } else {
      const shown = filterLibrary(this._library, this._query);
      body = shown.length
        ? html`<div class="grid">${shown.map((r) => this._renderTile(r))}</div>`
        : html`<div class="message">
            ${this._library.length ? `Nothing downloaded matches “${this._query.trim()}”.` : "Nothing downloaded yet."}
          </div>`;
    }
    return html`
      <div class="section stack">
        <span>Downloaded${this._library ? html` · ${filterLibrary(this._library, this._query).length}` : nothing}</span>
        <span class="hint">Newest first. Tap one to remove it or get more episodes.</span>
      </div>
      ${body}
    `;
  }

  private _renderWaiting() {
    if (this._waitingError) return html`<div class="message error">Couldn't load the Waiting list (${this._waitingError}).</div>`;
    if (!this._waiting) return html`<div class="message">Loading…</div>`;
    const shown = filterLibrary(this._waiting, this._query);
    const checkable = shown.filter((i) => i.state !== "downloading");
    return html`
      <div class="section stack">
        <span>Waiting · ${shown.length}</span>
        <span class="hint">Wanted but not downloaded yet: what's out, what isn't, and when.</span>
        <span class="hint">
          Sonarr and Radarr watch for new releases by themselves and download anything suitable. Check now runs an
          extra full search on demand.
        </span>
        ${checkable.length > 1
          ? html`<button class="secondary small checkall" ?disabled=${this._checkingAll} @click=${() => this._checkAll(checkable)}>
              ${this._checkingAll ? "Checking…" : "Check all now"}
            </button>`
          : nothing}
      </div>
      ${shown.length
        ? html`<div class="waiting">${shown.map((item) => this._renderWaitingRow(item))}</div>`
        : html`<div class="message">
            ${this._waiting.length ? `Nothing waiting matches “${this._query.trim()}”.` : "Nothing waiting: everything wanted is downloaded."}
          </div>`}
    `;
  }

  private _renderWaitingRow(item: WaitingItem) {
    const check = this._checks[this._key(item)];
    const checking = check === "checking";
    return html`
      <div class="wrow">
        <button class="wposter" ?disabled=${!item.tmdb_id} @click=${() => this._openWaiting(item)} aria-label=${item.title}>
          ${item.poster_url
            ? html`<img src=${item.poster_url} alt="" loading="lazy" />`
            : html`<ha-icon icon=${item.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
        </button>
        <div class="wbody">
          <div class="wtitle">
            <span>${item.title}${item.year ? html` <span class="count">(${item.year})</span>` : nothing}</span>
            <span class="status inline w-${item.state}">${waitingLabel(item)}</span>
          </div>
          <div class="hint">${waitingDetail(item)}</div>
          ${item.next_dub
            ? html`<div class="hint credit">Dub dates from <a href=${item.next_dub.url} target="_blank" rel="noreferrer">AnimeSchedule.net</a></div>`
            : nothing}
          ${typeof check === "object" ? html`<div class="wcheck">${checkSummary(check)}</div>` : nothing}
          ${typeof check === "string" && !checking ? html`<div class="wcheck error">${check}</div>` : nothing}
          ${item.state !== "downloading"
            ? html`<div class="wactions">
                <button class="secondary small" ?disabled=${checking || this._checkingAll} @click=${() => this._checkWaiting(item)}>
                  ${checking ? "Checking…" : "Check now"}
                </button>
                ${item.state === "not_found" || item.state === "dub_wanted"
                  ? html`<button class="secondary small" @click=${() => this._searchWaiting(item)}>Search again</button>`
                  : nothing}
              </div>`
            : nothing}
        </div>
      </div>
    `;
  }

  private _renderTile(r: SearchResult) {
    const chips = resultChips(r);
    return html`
      <button class="tile" @click=${() => this._open(r)} aria-label="${r.title} ${r.year ?? ""}">
        <div class="poster">
          ${r.poster_url
            ? html`<img src=${r.poster_url} alt="" loading="lazy" />`
            : html`<ha-icon icon=${r.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
          ${chips.length
            ? html`<span class="chipstack">${chips.map((c) => html`<span class="status ${c.cls}">${c.label}</span>`)}</span>`
            : nothing}
          <span class="kind">${r.media_type === "tv" ? "TV" : "Movie"}</span>
        </div>
        <div class="title">${r.title}</div>
        <div class="year">${r.year ?? ""}</div>
      </button>
    `;
  }

  private _renderDetail(item: SearchResult) {
    const label = statusLabel(item.status);
    const tv = item.media_type === "tv";
    const canRequest = tv
      ? canRequestMore(item.status) && (!this._seasons || this._chosen.size > 0)
      : isRequestable(item.status);
    return html`
      <div class="detail">
        <button class="back" @click=${this._back}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back
        </button>
        <div class="head">
          ${item.poster_url ? html`<img class="thumb" src=${item.poster_url} alt="" />` : nothing}
          <div>
            <h2>${item.title}</h2>
            <div class="meta">
              ${item.year ?? ""} · ${tv ? "TV show" : "Movie"}
              ${resultChips(item).map((c) => html`<span class="status inline ${c.cls}">${c.label}</span>`)}
            </div>
            ${this._release && releaseLine(this._release, item.media_type, new Date().toISOString().slice(0, 10))
              ? html`<div class="release">${releaseLine(this._release, item.media_type, new Date().toISOString().slice(0, 10))}</div>`
              : nothing}
            ${this._config.show_remove && isRemovable(item.status) && !this._confirmRemove
              ? html`<button class="danger small head-remove" @click=${this._remove}>
                  ${tv ? "Remove all…" : "Remove…"}
                </button>`
              : nothing}
          </div>
        </div>
        ${this._config.show_remove && isRemovable(item.status) && this._confirmRemove ? this._renderRemove(item) : nothing}
        ${item.overview ? html`<p class="overview">${item.overview}</p>` : nothing}
        ${this._renderAudio(item)}
        ${tv ? this._renderFollow(item) : nothing}
        ${tv ? this._renderSeasons() : nothing}
        ${this._config.show_4k && canRequest
          ? html`<label class="row">
              <input type="checkbox" .checked=${this._is4k} @change=${(e: Event) => (this._is4k = (e.target as HTMLInputElement).checked)} />
              Request in 4K
            </label>`
          : nothing}
        <button class="primary" ?disabled=${!canRequest || this._requesting || this._followBusy} @click=${this._request}>
          ${this._requesting
            ? "Requesting…"
            : this._followBusy && canRequest
              ? "Waiting for Get new episodes…"
              : canRequest
                ? "Request"
                : label ?? "Unavailable"}
        </button>
      </div>
    `;
  }

  /** The "are you sure" for Remove all / Remove, shown under the header. */
  private _renderRemove(item: SearchResult) {
    const what =
      item.media_type === "tv" ? `${item.title} and all its downloaded episodes` : `${item.title} and its file`;
    return html`
      <div class="confirm" role="alert">Delete ${what}? This can't be undone.</div>
      <div class="confirm-row">
        <button class="secondary" ?disabled=${this._removing} @click=${() => (this._confirmRemove = false)}>
          Cancel
        </button>
        <button class="danger solid" ?disabled=${this._removing} @click=${this._remove}>
          ${this._removing ? "Removing…" : "Delete files"}
        </button>
      </div>
    `;
  }

  private _renderSeasons() {
    if (this._seasonsError) {
      return html`<div class="message error">Couldn't load seasons (${this._seasonsError}). Request will ask for all.</div>`;
    }
    if (!this._seasons) return html`<div class="message">Loading seasons…</div>`;
    const open = requestableSeasons(this._seasons);
    return html`
      <div class="seasons">
        <div class="seasons-head">
          <span>Seasons</span>
          ${open.length > 1
            ? html`<button class="link" @click=${this._toggleAllSeasons}>
                ${this._chosen.size === open.length ? "Select none" : "Select all"}
              </button>`
            : nothing}
        </div>
        ${this._seasons.map((s) => {
          const free = isRequestable(s.status);
          const label = statusLabel(s.status);
          return html`<label class="row season ${free ? "" : "done"}">
            <input
              type="checkbox"
              .checked=${free ? this._chosen.has(s.season_number) : true}
              ?disabled=${!free}
              @change=${() => this._toggleSeason(s.season_number)}
            />
            <span class="grow">${s.name}</span>
            ${label ? html`<span class="status inline ${s.status}">${label}</span>` : nothing}
            ${this._picker
              ? html`<button class="link episodes-link" @click=${(e: Event) => this._openEpisodes(s, e)}>
                  Episodes
                </button>`
              : nothing}
          </label>`;
        })}
      </div>
    `;
  }

  private _renderEpisodes(item: SearchResult, season: Season) {
    const list = this._episodes;
    let body;
    if (this._episodesError) {
      body = html`<div class="message error">Couldn't load episodes (${this._episodesError}).</div>`;
    } else if (!list) {
      body = html`<div class="message">Loading episodes from Sonarr…</div>`;
    } else {
      const open = pickableEpisodes(list.episodes);
      const n = this._picked.size;
      const choice = this._audio?.audio ?? null;
      const latest = Math.max(...(this._seasons ?? []).map((s) => s.season_number), list.season_number) === list.season_number;
      const dubWanted = choice === "dub" || choice === "dub_only";
      body = html`
        <div class="seasons">
          <div class="seasons-head">
            <span>${list.episodes.length} episodes</span>
            ${open.length > 1
              ? html`<button class="link" @click=${this._toggleAllPicks}>
                  ${n === open.length ? "Select none" : `Select all ${open.length}`}
                </button>`
              : nothing}
          </div>
          ${list.episodes.length
            ? list.episodes.map((ep) => {
                const free = isPickable(ep);
                const label = episodeLabel(ep, choice);
                const audio = episodeAudioLabel(ep);
                const dubLine = dubWanted ? episodeDubLine(ep, this._audio?.dub ?? null, latest) : null;
                return html`<label class="row season episode ${free ? "" : "done"}">
                  <input
                    type="checkbox"
                    .checked=${free ? this._picked.has(ep.id) : ep.status !== "not_aired" || ep.monitored}
                    ?disabled=${!free}
                    @change=${() => this._togglePick(ep.id)}
                  />
                  <span class="grow">
                    <span class="ep-title">${ep.episode_number}. ${ep.title || `Episode ${ep.episode_number}`}</span>
                    <span class="hint">${airDateLabel(ep.air_date)}${dubLine ? html` · ${dubLine}` : nothing}</span>
                  </span>
                  <span class="epchips">
                    ${label ? html`<span class="status inline ep ${ep.status}">${label}</span>` : nothing}
                    ${audio ? html`<span class="status inline ep audio-${ep.audio}">${audio}</span>` : nothing}
                  </span>
                  ${this._config.show_remove && ep.status === "downloaded" && this._confirmRemoveEp !== ep.id
                    ? html`<button class="link ep-remove" @click=${(e: Event) => this._askRemoveEpisode(ep.id, e)}>
                        Remove
                      </button>`
                    : nothing}
                </label>
                ${this._confirmRemoveEp === ep.id
                  ? html`<div class="ep-confirm" role="alert">
                      <span class="grow">Delete episode ${ep.episode_number}'s file? This can't be undone.</span>
                      <button class="secondary small" ?disabled=${this._pickerBusy} @click=${() => (this._confirmRemoveEp = undefined)}>
                        Cancel
                      </button>
                      <button class="danger solid small" ?disabled=${this._pickerBusy} @click=${() => this._removeEpisode(ep)}>
                        ${this._pickerBusy ? "Deleting…" : "Delete file"}
                      </button>
                    </div>`
                  : nothing}`;
              })
            : html`<div class="message">Sonarr lists no episodes for this season yet.</div>`}
        </div>
        ${n > 20
          ? html`<div class="warn">That's ${n} episodes. Check there's room before downloading.</div>`
          : nothing}
        <button class="primary" ?disabled=${!n || this._pickerBusy} @click=${this._download}>
          ${this._downloading
            ? "Searching… (carries on if you leave)"
            : this._pickerBusy
              ? "Working…"
              : n
                ? `Download ${n} episode${n === 1 ? "" : "s"}`
                : "Pick episodes to download"}
        </button>
      `;
    }
    return html`
      <div class="detail">
        <button class="back" @click=${this._closeEpisodes}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> ${item.title}
        </button>
        <div class="ep-head">
          <h2>${season.name}</h2>
          <div class="meta">Episodes from Sonarr</div>
          ${this._audio?.dub && (this._audio.audio === "dub" || this._audio.audio === "dub_only")
            ? html`<div class="hint credit">Dub dates from <a href=${this._audio.dub.url} target="_blank" rel="noreferrer">AnimeSchedule.net</a></div>`
            : nothing}
        </div>
        ${body}
      </div>
    `;
  }

  static override styles = css`
    :host {
      --js-gap: 12px;
      --js-radius: var(--ha-card-border-radius, 12px);
    }
    .stale {
      margin: var(--js-gap);
      padding: 8px 12px;
      border-radius: 8px;
      background: var(--warning-color, #ffa600);
      color: var(--text-primary-color, #fff);
    }
    .search {
      padding: var(--js-gap) var(--js-gap) 0;
    }
    .field {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 8px 0 12px;
      border-radius: 24px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    input[type="search"] {
      flex: 1;
      min-width: 0;
      height: 44px;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--primary-text-color);
      font: inherit;
      font-size: 16px; /* Below 16px iOS zooms the page on focus. */
    }
    input[type="search"]::-webkit-search-cancel-button {
      display: none;
    }
    button {
      font: inherit;
      color: inherit;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .icon {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border: 0;
      border-radius: 50%;
      background: none;
    }
    .chips {
      display: flex;
      gap: 8px;
      padding: 10px 0 4px;
    }
    .chip {
      padding: 6px 14px;
      border-radius: 16px;
      border: 1px solid var(--divider-color);
      background: none;
      color: var(--primary-text-color);
    }
    .chip.on {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .message {
      padding: var(--js-gap);
      color: var(--secondary-text-color);
    }
    .message.error {
      color: var(--error-color);
    }
    .section {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: var(--js-gap) var(--js-gap) 0;
      font-weight: 500;
      color: var(--secondary-text-color);
    }
    .chips.small {
      padding: 0;
    }
    .chips.small .chip {
      padding: 3px 10px;
      font-size: 13px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
      gap: var(--js-gap);
      padding: var(--js-gap);
      transition: opacity 0.2s;
    }
    .grid.busy {
      opacity: 0.5;
    }
    .tile {
      display: flex;
      flex-direction: column;
      padding: 0;
      border: 0;
      background: none;
      text-align: start;
      min-width: 0;
    }
    .poster {
      position: relative;
      aspect-ratio: 2 / 3;
      border-radius: 8px;
      overflow: hidden;
      display: grid;
      place-items: center;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      --mdc-icon-size: 40px;
    }
    .poster img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .status,
    .kind {
      position: absolute;
      padding: 2px 6px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 500;
      line-height: 16px;
    }
    .status {
      top: 6px;
      right: 6px;
      background: var(--info-color, #039be5);
      color: #fff;
    }
    .status.available {
      background: var(--success-color, #43a047);
    }
    .status.partially_available {
      background: var(--warning-color, #ffa600);
    }
    .status.blacklisted {
      background: var(--error-color, #db4437);
    }
    .status.inline {
      position: static;
      margin-inline-start: 6px;
    }
    .kind {
      bottom: 6px;
      left: 6px;
      background: rgba(0, 0, 0, 0.6);
      color: #fff;
    }
    .title {
      margin-top: 6px;
      font-size: 13px;
      font-weight: 500;
      color: var(--primary-text-color);
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .year {
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    .detail {
      display: flex;
      flex-direction: column;
      gap: var(--js-gap);
      padding: var(--js-gap);
    }
    .back {
      align-self: flex-start;
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 8px 6px 4px;
      border: 0;
      border-radius: 8px;
      background: none;
      color: var(--primary-color);
    }
    .head {
      display: flex;
      gap: var(--js-gap);
      align-items: flex-start;
    }
    .thumb {
      width: 88px;
      aspect-ratio: 2 / 3;
      object-fit: cover;
      border-radius: 8px;
      flex: none;
    }
    h2 {
      margin: 0 0 4px;
      font-size: 20px;
      line-height: 1.25;
      font-weight: 500;
      color: var(--primary-text-color);
    }
    .meta,
    .count {
      color: var(--secondary-text-color);
      font-size: 14px;
    }
    .overview {
      margin: 0;
      color: var(--primary-text-color);
      line-height: 1.45;
    }
    .seasons {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      overflow: hidden;
    }
    .seasons-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      font-weight: 500;
      background: var(--secondary-background-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 44px;
    }
    .season {
      padding: 0 12px;
      border-top: 1px solid var(--divider-color);
    }
    .season.done {
      color: var(--secondary-text-color);
    }
    .episodes-link {
      flex: none;
      font-size: 14px;
    }
    .option {
      padding: 6px 12px;
    }
    .option + .option {
      border-top: 1px solid var(--divider-color);
    }
    .hint {
      display: block;
      color: var(--secondary-text-color);
      font-size: 12px;
      line-height: 1.3;
    }
    .episode {
      padding-block: 6px;
    }
    .ep-title {
      display: block;
      line-height: 1.3;
    }
    .ep-head h2 {
      margin: 0;
    }
    .status.ep {
      flex: none;
    }
    .status.downloaded {
      background: var(--success-color, #43a047);
    }
    .status.not_aired {
      background: var(--secondary-text-color, #727272);
    }
    .head-remove {
      margin-top: 10px;
      align-self: flex-start;
    }
    .link.ep-remove {
      flex: none;
      font-size: 14px;
      color: var(--error-color, #db4437);
    }
    .ep-confirm {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 12px 10px;
      color: var(--error-color, #db4437);
      font-size: 14px;
      line-height: 1.35;
    }
    .ep-confirm .grow {
      flex-basis: 100%;
    }
    .small {
      height: 36px;
      padding: 0 16px;
      font-size: 14px;
    }
    .section.stack {
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
    }
    .section.stack .hint {
      font-weight: 400;
    }
    .hint.busy {
      color: var(--primary-color);
    }
    .chips {
      flex-wrap: wrap;
    }
    /* Streaming pickers: eleven services and a dozen genres would fill a phone
       screen wrapped, so each row scrolls sideways instead. */
    .chips.scroll {
      flex-wrap: nowrap;
      overflow-x: auto;
      scrollbar-width: none;
      padding: 8px var(--js-gap) 0;
    }
    .chips.scroll::-webkit-scrollbar {
      display: none;
    }
    .chips.scroll .chip {
      flex: none;
      white-space: nowrap;
    }
    .section .heading {
      white-space: nowrap;
    }
    /* Heading and Trending / Popular / Streaming share a line when they fit;
       on a phone the switch drops below the heading rather than wrapping a chip. */
    .section.browse {
      flex-wrap: wrap;
      row-gap: 6px;
    }
    .section.browse .chips.small {
      flex-wrap: nowrap;
    }
    /* TMDB's watch-provider data must be credited to JustWatch (TMDB API docs, "Watch Providers"). */
    .attribution {
      padding: 0 var(--js-gap) var(--js-gap);
      font-size: 11px;
      text-align: center;
      color: var(--secondary-text-color);
    }
    .more {
      display: flex;
      justify-content: center;
      padding: 0 var(--js-gap) var(--js-gap);
    }
    .chipstack {
      position: absolute;
      top: 6px;
      right: 6px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }
    .chipstack .status {
      position: static;
    }
    .status.wanted {
      background: var(--secondary-text-color, #727272);
    }
    .checkall {
      margin-top: 6px;
    }
    .waiting {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 8px var(--js-gap) var(--js-gap);
    }
    .wrow {
      display: flex;
      gap: 12px;
      padding: 10px;
      border: 1px solid var(--divider-color);
      border-radius: 10px;
    }
    .wposter {
      flex: none;
      width: 56px;
      height: 84px;
      padding: 0;
      border: 0;
      border-radius: 6px;
      overflow: hidden;
      background: var(--secondary-background-color);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .wposter img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .wbody {
      min-width: 0;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .wtitle {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      font-weight: 500;
      line-height: 1.3;
    }
    .wtitle .status {
      flex: none;
    }
    .status.w-not_out {
      background: var(--secondary-text-color, #727272);
    }
    .status.w-not_found {
      background: var(--warning-color, #ffa600);
    }
    .status.w-dub_wanted {
      background: var(--secondary-text-color, #727272);
    }
    /* Audio: English (dub, dual audio, all dubbed) green-blue; part dubbed amber;
       Japanese only grey. */
    .status.audio-dub,
    .status.audio-dual {
      background: var(--state-active-color, #009688);
    }
    .status.audio-part_dub {
      background: var(--warning-color, #ffa600);
    }
    .status.audio-sub,
    .status.audio-sub_only {
      background: var(--secondary-text-color, #727272);
    }
    .epchips {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
      flex: none;
    }
    .audio {
      padding-bottom: 10px;
    }
    .audio .option {
      border-top: 1px solid var(--divider-color);
    }
    .audio .confirm,
    .audio .confirm-row,
    .audio .audio-line,
    .audio .credit,
    .audio-note {
      margin: 8px 12px 0;
    }
    .confirm.notice {
      color: var(--primary-text-color);
    }
    .credit {
      font-size: 12px;
    }
    .credit a {
      color: var(--primary-color);
    }
    .wcheck {
      font-size: 13px;
      line-height: 1.35;
    }
    .wcheck.error {
      color: var(--error-color, #db4437);
    }
    .wactions {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }
    .release {
      margin-top: 4px;
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .warn {
      color: var(--warning-color, #ffa600);
      line-height: 1.4;
    }
    .row input {
      width: 20px;
      height: 20px;
      accent-color: var(--primary-color);
    }
    .grow {
      flex: 1;
    }
    .link {
      border: 0;
      background: none;
      color: var(--primary-color);
      padding: 4px;
    }
    .primary {
      height: 44px;
      border: 0;
      border-radius: 22px;
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      font-weight: 500;
    }
    .danger,
    .secondary {
      height: 44px;
      border-radius: 22px;
      font-weight: 500;
      background: none;
    }
    .danger {
      border: 1px solid var(--error-color, #db4437);
      color: var(--error-color, #db4437);
    }
    .danger.solid {
      background: var(--error-color, #db4437);
      color: #fff;
    }
    .secondary {
      border: 1px solid var(--divider-color);
      color: var(--primary-text-color);
    }
    .confirm {
      color: var(--error-color, #db4437);
      line-height: 1.4;
    }
    .confirm-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--js-gap);
    }
    .danger[disabled],
    .secondary[disabled] {
      opacity: 0.6;
      cursor: default;
    }
    .primary[disabled] {
      background: var(--disabled-color, #bdbdbd);
      cursor: default;
    }
  `;
}

if (!customElements.get("jellyseerr-search-card")) {
  customElements.define("jellyseerr-search-card", JellyseerrSearchCard);
  window.customCards = window.customCards ?? [];
  window.customCards.push({
    type: "jellyseerr-search-card",
    name: "Jellyseerr Search",
    description: "Search movies and TV shows and request them through Jellyseerr.",
    preview: false,
  });
}
