// <jellyseerr-search-card>: search Jellyseerr and request movies or shows.

import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { errorMessage, toast, type HomeAssistant } from "./ha";
import { Latest, canRequestMore, isRequestable, requestableSeasons, statusLabel } from "./logic";
import type { CardConfig, MediaFilter, SearchResult, Season } from "./types";

export const CARD_VERSION = __CARD_VERSION__;
const DOMAIN = "jellyseerr_search";
const DEBOUNCE_MS = 400;
const MIN_QUERY = 2;
// A wall-mounted tablet keeps the card open for days; refetch trending after this.
const TRENDING_TTL_MS = 60 * 60 * 1000;

let versionChecked = false;

const FILTERS: Array<{ value: MediaFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV" },
];

export class JellyseerrSearchCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    _config: { state: true },
    _query: { state: true },
    _filter: { state: true },
    _results: { state: true },
    _trending: { state: true },
    _trendingError: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _selected: { state: true },
    _seasons: { state: true },
    _seasonsError: { state: true },
    _chosen: { state: true },
    _is4k: { state: true },
    _requesting: { state: true },
    _staleVersion: { state: true },
  };

  declare hass: HomeAssistant;
  declare _config: CardConfig;
  declare _query: string;
  declare _filter: MediaFilter;
  declare _results?: SearchResult[];
  declare _trending?: SearchResult[];
  declare _trendingError?: string;
  declare _loading: boolean;
  declare _error?: string;
  declare _selected?: SearchResult;
  declare _seasons?: Season[];
  declare _seasonsError?: string;
  declare _chosen: Set<number>;
  declare _is4k: boolean;
  declare _requesting: boolean;
  declare _staleVersion?: string;

  private _debounce?: ReturnType<typeof setTimeout>;
  private _latestSearch = new Latest();
  private _latestSeasons = new Latest();
  private _latestTrending = new Latest();
  private _trendingAt = 0;
  private _trendingFilter?: MediaFilter;

  constructor() {
    super();
    this._query = "";
    this._filter = "all";
    this._loading = false;
    this._chosen = new Set();
    this._is4k = false;
    this._requesting = false;
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
        { name: "show_4k", selector: { boolean: {} } },
        { name: "config_entry_id", selector: { config_entry: { integration: DOMAIN } } },
      ],
      computeLabel: (field: { name: string }) =>
        ({
          title: "Title",
          media_type: "Default filter",
          show_trending: "Show trending titles before searching",
          show_4k: "Offer 4K requests",
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
    return this._results?.length || (this._showTrending() && this._trending?.length) ? 8 : 2;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    clearTimeout(this._debounce);
  }

  protected override updated(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass && !versionChecked) {
      versionChecked = true;
      void this._checkVersion();
    }
    if (changed.has("hass") && this.hass && this._trendingDue()) void this._loadTrending();
  }

  /** A cached old card talking to a newer backend: offer a cache-clearing reload. */
  private async _checkVersion(): Promise<void> {
    try {
      const { version } = await this.hass.callWS<{ version: string }>({ type: `${DOMAIN}/version` });
      if (version !== CARD_VERSION) this._staleVersion = version;
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

  // --- trending -----------------------------------------------------------

  private _showTrending(): boolean {
    return this._config.show_trending !== false && this._query.trim().length < MIN_QUERY;
  }

  /** Missing, for another filter, or older than the TTL, and on screen. */
  private _trendingDue(): boolean {
    if (!this._showTrending() || this._selected) return false;
    if (this._trendingFilter !== this._filter) return true;
    return Date.now() - this._trendingAt > TRENDING_TTL_MS;
  }

  private async _loadTrending(): Promise<void> {
    const current = this._latestTrending.next();
    const filter = this._filter;
    // Set before the call so the frequent hass updates don't refetch meanwhile.
    this._trendingFilter = filter;
    this._trendingAt = Date.now();
    this._trendingError = undefined;
    try {
      const { results } = await this.hass.callWS<{ results: SearchResult[] }>({
        type: `${DOMAIN}/trending`,
        media_type: filter,
        ...this._entry(),
      });
      if (current()) this._trending = results;
    } catch (err) {
      if (current()) this._trendingError = errorMessage(err);
    }
  }

  // --- search -------------------------------------------------------------

  private _onInput(ev: InputEvent): void {
    this._query = (ev.target as HTMLInputElement).value;
    clearTimeout(this._debounce);
    this._debounce = setTimeout(() => void this._search(), DEBOUNCE_MS);
  }

  private _onKeydown(ev: KeyboardEvent): void {
    if (ev.key !== "Enter") return;
    clearTimeout(this._debounce);
    (ev.target as HTMLInputElement).blur(); // Drops the phone keyboard so results are visible.
    void this._search();
  }

  private _clear(): void {
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
    if (this._query.trim().length >= MIN_QUERY) void this._search();
    else if (this._trendingDue()) void this._loadTrending();
  }

  private async _search(): Promise<void> {
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
    this._selected = result;
    this._seasons = undefined;
    this._seasonsError = undefined;
    this._chosen = new Set();
    this._is4k = false;
    if (result.media_type === "tv") void this._loadSeasons(result.tmdb_id);
  }

  private async _loadSeasons(tmdbId: number): Promise<void> {
    const current = this._latestSeasons.next();
    try {
      const { seasons } = await this.hass.callWS<{ seasons: Season[] }>({
        type: `${DOMAIN}/seasons`,
        tmdb_id: tmdbId,
        ...this._entry(),
      });
      if (!current()) return;
      this._seasons = seasons;
      this._chosen = new Set(requestableSeasons(seasons));
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
    const msg: Record<string, unknown> = {
      type: `${DOMAIN}/request`,
      tmdb_id: item.tmdb_id,
      media_type: item.media_type,
      is_4k: this._is4k,
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
    } catch (err) {
      toast(this, `Request failed: ${errorMessage(err)}`);
    } finally {
      this._requesting = false;
    }
  }

  /** Show the new state right away instead of waiting for a re-search. */
  private _markRequested(item: SearchResult): void {
    const status = item.status === "partially_available" ? item.status : "pending";
    const updated = { ...item, status } as SearchResult;
    const swap = (list?: SearchResult[]) =>
      list?.map((r) => (r.tmdb_id === item.tmdb_id && r.media_type === item.media_type ? updated : r));
    this._results = swap(this._results);
    this._trending = swap(this._trending);
    if (this._selected === item) this._selected = updated;
    if (this._seasons) {
      this._seasons = this._seasons.map((s) =>
        this._chosen.has(s.season_number) ? { ...s, status: "pending" } : s,
      );
      this._chosen = new Set();
    }
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
        ${this._selected ? this._renderDetail(this._selected) : this._renderSearch()}
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
          ${FILTERS.map(
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
    if (this._showTrending()) return this._renderTrending();
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

  private _renderTrending() {
    if (this._trendingError) {
      return html`<div class="message error">Couldn't load trending (${this._trendingError}).</div>`;
    }
    if (!this._trending) return html`<div class="message">Loading trending…</div>`;
    if (!this._trending.length) return nothing;
    return html`
      <div class="section">Trending today</div>
      <div class="grid">${this._trending.map((r) => this._renderTile(r))}</div>
    `;
  }

  private _renderTile(r: SearchResult) {
    const label = statusLabel(r.status);
    return html`
      <button class="tile" @click=${() => this._open(r)} aria-label="${r.title} ${r.year ?? ""}">
        <div class="poster">
          ${r.poster_url
            ? html`<img src=${r.poster_url} alt="" loading="lazy" />`
            : html`<ha-icon icon=${r.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
          ${label ? html`<span class="status ${r.status}">${label}</span>` : nothing}
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
        <button class="back" @click=${() => (this._selected = undefined)}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back
        </button>
        <div class="head">
          ${item.poster_url ? html`<img class="thumb" src=${item.poster_url} alt="" />` : nothing}
          <div>
            <h2>${item.title}</h2>
            <div class="meta">
              ${item.year ?? ""} · ${tv ? "TV show" : "Movie"}
              ${label ? html`<span class="status inline ${item.status}">${label}</span>` : nothing}
            </div>
          </div>
        </div>
        ${item.overview ? html`<p class="overview">${item.overview}</p>` : nothing}
        ${tv ? this._renderSeasons() : nothing}
        ${this._config.show_4k && canRequest
          ? html`<label class="row">
              <input type="checkbox" .checked=${this._is4k} @change=${(e: Event) => (this._is4k = (e.target as HTMLInputElement).checked)} />
              Request in 4K
            </label>`
          : nothing}
        <button class="primary" ?disabled=${!canRequest || this._requesting} @click=${this._request}>
          ${this._requesting ? "Requesting…" : canRequest ? "Request" : label ?? "Unavailable"}
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
            <span class="count">${s.episode_count} ep</span>
            ${label ? html`<span class="status inline ${s.status}">${label}</span>` : nothing}
          </label>`;
        })}
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
      padding: var(--js-gap) var(--js-gap) 0;
      font-weight: 500;
      color: var(--secondary-text-color);
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
