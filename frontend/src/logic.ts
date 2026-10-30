// Pure helpers, kept out of the card so vitest can cover them without a DOM.

import type {
  AudioChoice,
  AudioState,
  AudioSummary,
  CheckResult,
  DubInfo,
  Episode,
  MediaFilter,
  MediaStatus,
  MediaType,
  ReleaseInfo,
  SearchResult,
  Season,
  StreamSort,
  WaitingItem,
} from "./types";

const REQUESTABLE: ReadonlySet<MediaStatus> = new Set(["not_requested", "unknown", "deleted"]);

export function isRequestable(status: MediaStatus): boolean {
  return REQUESTABLE.has(status);
}

/** Short chip text for a status, or null when there is nothing worth showing. */
export function statusLabel(status: MediaStatus): string | null {
  switch (status) {
    case "pending":
      return "Requested";
    case "processing":
      return "Processing";
    case "partially_available":
      return "Partial";
    case "available":
      return "Available";
    case "blacklisted":
      return "Blocked";
    default:
      return null;
  }
}

/** The chips on a result: Downloaded and/or Waiting from Sonarr/Radarr when they
 *  know the title, else Jellyseerr's status. `cls` picks the colour. */
export function resultChips(r: SearchResult): Array<{ label: string; cls: string }> {
  if (r.arr && (r.arr.downloaded || r.arr.waiting)) {
    const chips: Array<{ label: string; cls: string }> = [];
    if (r.arr.downloaded) chips.push({ label: "Downloaded", cls: "available" });
    if (r.arr.waiting) chips.push({ label: "Waiting", cls: "wanted" });
    if (r.arr.audio) chips.push({ label: AUDIO_SUMMARY[r.arr.audio], cls: `audio-${r.arr.audio}` });
    return chips;
  }
  const label = statusLabel(r.status);
  return label ? [{ label, cls: r.status }] : [];
}

/** Titles Radarr/Sonarr hold (or are fetching), so Remove has something to delete. */
export function isRemovable(status: MediaStatus): boolean {
  return status === "available" || status === "partially_available" || status === "processing";
}

/** Seasons that can still be requested: the default selection in the picker. */
export function requestableSeasons(seasons: readonly Season[]): number[] {
  return seasons.filter((s) => isRequestable(s.status)).map((s) => s.season_number);
}

/** A partially available show still has seasons to ask for; a full one doesn't. */
export function canRequestMore(status: MediaStatus): boolean {
  return isRequestable(status) || status === "partially_available";
}

/** Episodes the picker can still tick: not on disk, not on the way, not already wanted. */
export function isPickable(ep: Episode): boolean {
  return ep.status === "missing" || (ep.status === "not_aired" && !ep.monitored);
}

export function pickableEpisodes(episodes: readonly Episode[]): number[] {
  return episodes.filter(isPickable).map((e) => e.id);
}

/** Chip text for an episode, or null for one that can still be picked. On
 *  "dub only", a wanted episode is waiting for its dub. */
export function episodeLabel(ep: Episode, audio: AudioChoice | null = null): string | null {
  switch (ep.status) {
    case "downloaded":
      return "Downloaded";
    case "downloading":
      return "Downloading";
    case "wanted":
      return audio === "dub_only" ? "Waiting for dub" : "Not found yet";
    case "not_aired":
      return ep.monitored ? "When it airs" : "Not aired";
    default:
      return null;
  }
}

/** "4 Nov 2026" from Sonarr's YYYY-MM-DD, without time-zone surprises. */
export function airDateLabel(date: string | null): string {
  if (!date) return "No air date";
  const [y, m, d] = date.split("-").map(Number);
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
  return month ? `${d} ${month} ${y}` : date;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "22 Oct 2026" from a YYYY-MM-DD day (no time-zone shift). */
function day(date: string): string {
  const [y, m, d] = date.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** "today 15:00", "tomorrow 15:00" or "Fri 30 Oct, 15:00", in the viewer's time zone. */
export function airTime(utc: string, now: Date = new Date()): string {
  const t = new Date(utc);
  const hhmm = t.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOf(t) - startOf(now)) / 86_400_000);
  if (days === 0) return `today ${hhmm}`;
  if (days === 1) return `tomorrow ${hhmm}`;
  const date = t.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
  return `${date}, ${hhmm}`;
}

/** "3 hours ago" / "2 days ago" for a last-searched time. */
export function ago(iso: string, now: Date = new Date()): string {
  const mins = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60_000));
  if (mins < 60) return mins <= 1 ? "just now" : `${mins} minutes ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export function waitingLabel(item: WaitingItem): string {
  if (item.state === "not_found" && item.audio === "dub_only") return "Waiting for dub";
  return { downloading: "Downloading", not_found: "Not found yet", not_out: "Not out yet", dub_wanted: "Waiting for dub" }[
    item.state
  ];
}

/** The line under a Waiting title: when it's out, or what it's waiting for. */
export function waitingDetail(item: WaitingItem, now: Date = new Date()): string {
  if (item.state === "downloading") return "Downloading now.";
  if (item.media_type === "tv") {
    const parts: string[] = [];
    const dubOnly = item.audio === "dub_only";
    if (item.missing) {
      const s = item.missing === 1 ? "" : "s";
      parts.push(dubOnly ? `${item.missing} episode${s} out, no dub found yet` : `${item.missing} episode${s} out but not found yet`);
    }
    if (item.dub_wanted) parts.push(`${item.dub_wanted} episode${item.dub_wanted === 1 ? "" : "s"} in Japanese, dub wanted`);
    if (item.next_dub && item.next_dub.date_utc) parts.push(`Next dub: E${item.next_dub.episode} ${airTime(item.next_dub.date_utc, now)}`);
    const n = item.next_episode;
    if (n) parts.push(`Next: S${n.season}E${n.episode} ${airTime(n.air_date_utc, now)}`);
    if (item.state === "not_found" && item.last_search) parts.push(`last searched ${ago(item.last_search, now)}`);
    return parts.length ? parts.join(" · ") : "No upcoming episodes listed yet.";
  }
  if (item.state === "not_found") {
    const out = item.digital_release ?? item.physical_release;
    const since = out ? `Out since ${day(out)}` : "Out";
    return item.last_search ? `${since} · last searched ${ago(item.last_search, now)}` : since;
  }
  // Not out yet.
  if (item.expected_basis === "digital") return `Digital release ${day(item.expected!)}`;
  if (item.expected_basis === "physical") return `Blu-ray/DVD release ${day(item.expected!)}`;
  if (item.expected_basis === "cinema_plus_90" && item.in_cinemas) {
    const cinema = `In cinemas from ${day(item.in_cinemas)}`;
    return `${cinema} · no home release date yet (counted as out around ${day(item.expected!)})`;
  }
  return item.release_status === "announced" ? "Announced · no release date yet" : "No release date yet";
}

/** What an indexer check means, in a sentence. */
export function checkSummary(result: CheckResult): string {
  const what = result.episode ? ` for S${result.episode.season}E${result.episode.episode}` : "";
  if (!result.found) return `Nothing posted yet${what}.`;
  if (result.accepted) {
    const english = result.dubbed ? ` (${result.dubbed} with English audio)` : "";
    return `${result.accepted} suitable cop${result.accepted === 1 ? "y" : "ies"} found${what}${english}${result.best ? `: ${result.best}` : ""}.`;
  }
  const why = result.reasons.length ? ` (${result.reasons[0]})` : "";
  return `${result.found} cop${result.found === 1 ? "y" : "ies"} found${what}, none your profile accepts${why}.`;
}

/** "Is it out?" for a title's page, from TMDB's dates. `today` is YYYY-MM-DD. */
export function releaseLine(info: ReleaseInfo, mediaType: "movie" | "tv", today: string): string | null {
  if (mediaType === "tv") {
    if (info.next_air_date) return `Next episode ${day(info.next_air_date)}`;
    if (info.tmdb_status === "Ended" || info.tmdb_status === "Canceled") return `Ended${info.last_air_date ? ` · last aired ${day(info.last_air_date)}` : ""}`;
    return info.last_air_date ? `No next episode announced · last aired ${day(info.last_air_date)}` : null;
  }
  const home = [info.digital, info.physical].filter((d): d is string => !!d).sort()[0];
  if (home && home <= today) return `Out to buy or stream since ${day(home)}`;
  if (info.digital && info.digital > today) return `Digital release ${day(info.digital)}`;
  if (info.physical && info.physical > today) return `Blu-ray/DVD release ${day(info.physical)}`;
  if (info.theatrical && info.theatrical <= today) return `In cinemas from ${day(info.theatrical)} · no digital release date yet`;
  if (info.theatrical) return `In cinemas ${day(info.theatrical)}`;
  if (info.tmdb_status && info.tmdb_status !== "Released") return `Not released yet (${info.tmdb_status.toLowerCase()})`;
  return null;
}

export const AUDIO_SUMMARY: Record<AudioSummary, string> = { dub: "Dub", part_dub: "Part dub", sub_only: "Sub only" };

/** The page's audio options, in order, with what each does. */
export const AUDIO_OPTIONS: ReadonlyArray<{ value: AudioChoice; label: string; hint: string }> = [
  {
    value: "dub",
    label: "English dub, subtitles until it's out",
    hint: "Japanese with subtitles now, replaced by the English dub when it's posted.",
  },
  { value: "dub_only", label: "English dub only", hint: "Nothing downloads until an English dub is posted." },
  { value: "sub", label: "Japanese with subtitles", hint: "Dubs aren't downloaded." },
];

/** What switching an existing title to `to` will do, for the confirmation. */
export function audioSwitchWarning(to: AudioChoice, mediaType: "movie" | "tv"): string {
  const what = mediaType === "tv" ? "episodes" : "the film";
  if (to === "sub") return `Dubs stop downloading, and dubbed ${what} may be swapped for Japanese copies as they're posted.`;
  return mediaType === "tv"
    ? "Searches now for English dubs of the episodes still in Japanese. Each replacement downloads again (about 1 GB an episode)."
    : "Searches now for an English dub. If one's found, the film downloads again.";
}

/** Chip text for a downloaded episode's audio, or null when there's no file or
 *  its tracks aren't tagged. */
export function episodeAudioLabel(ep: Episode): string | null {
  switch (ep.audio) {
    case "dual":
      return "Dual audio";
    case "dub":
      return "Dub";
    case "sub":
      return ep.english_subs ? "Sub · Eng subs" : "Sub";
    default:
      return null;
  }
}

/** When this episode's dub is expected, from the next dub in the timetable and
 *  its weekly rhythm; null for episodes already in English or before it. The
 *  timetable counts episodes within the season, so only the latest season. */
export function episodeDubLine(ep: Episode, dub: DubInfo | null, latestSeason: boolean, now: Date = new Date()): string | null {
  if (!dub?.date_utc || !dub.episode || !latestSeason || ep.audio === "dual" || ep.audio === "dub") return null;
  const ahead = ep.episode_number - dub.episode;
  if (ahead < 0) return null;
  if (ahead === 0) return `Dub ${airTime(dub.date_utc, now)}`;
  const when = new Date(new Date(dub.date_utc).getTime() + ahead * 7 * 86_400_000);
  return `Dub expected around ${when.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`;
}

/** The page's dub lines: what's downloaded in English, and the next dub. */
export function audioLines(state: AudioState, mediaType: "movie" | "tv", now: Date = new Date()): string[] {
  const lines: string[] = [];
  if (state.files) {
    if (mediaType === "movie") lines.push(state.english_files ? "Downloaded with English audio." : "Downloaded in Japanese.");
    else if (state.english_files === state.files) lines.push(`All ${state.files} downloaded episodes have English audio.`);
    else lines.push(`${state.english_files} of ${state.files} downloaded episodes have English audio.`);
  }
  const dub = state.dub;
  if (dub?.date_utc && dub.episode) {
    const upTo = dub.last_episode ? ` · dubbed up to episode ${dub.last_episode}` : "";
    lines.push(`English dub: episode ${dub.episode} ${airTime(dub.date_utc, now)}${dub.delayed ? " (delayed)" : ""}${upTo}`);
  } else if (dub?.last_episode) {
    lines.push(`English dub: up to episode ${dub.last_episode}, no next date listed`);
  } else if (state.dub_dates && mediaType === "tv") {
    lines.push("No English dub dates listed for the next 4 weeks.");
  }
  return lines;
}

/**
 * Services the Streaming list can show, in the default order. `id` is TMDB's
 * watch provider id, the same in every country (what each service carries
 * differs by country). Read from Seerr's /watchproviders for GB 2026-10-30.
 */
export const SERVICES: ReadonlyArray<{ key: string; label: string; id: number }> = [
  { key: "netflix", label: "Netflix", id: 8 },
  { key: "disney", label: "Disney+", id: 337 },
  { key: "crunchyroll", label: "Crunchyroll", id: 283 },
  { key: "prime", label: "Prime Video", id: 9 },
  { key: "apple", label: "Apple TV", id: 350 },
  { key: "now", label: "NOW", id: 39 },
  { key: "iplayer", label: "BBC iPlayer", id: 38 },
  { key: "itvx", label: "ITVX", id: 41 },
  { key: "channel4", label: "Channel 4", id: 103 },
  { key: "paramount", label: "Paramount+", id: 531 },
  { key: "skygo", label: "Sky Go", id: 29 },
];

/** The configured services in the configured order; all of them when none are set. */
export function servicesFor(keys?: readonly string[]): typeof SERVICES {
  if (!keys?.length) return SERVICES;
  const picked = keys.map((k) => SERVICES.find((s) => s.key === k)).filter((s) => s !== undefined);
  return picked.length ? picked : SERVICES;
}

/**
 * Genres the Streaming list offers. Keys match the server's BROWSE_GENRES;
 * `types` are the ones TMDB has that genre for (no Horror for TV, no Reality for film).
 */
export const GENRES: ReadonlyArray<{ key: string; label: string; types: ReadonlyArray<MediaType> }> = [
  { key: "action", label: "Action & Adventure", types: ["movie", "tv"] },
  { key: "comedy", label: "Comedy", types: ["movie", "tv"] },
  { key: "drama", label: "Drama", types: ["movie", "tv"] },
  { key: "crime", label: "Crime", types: ["movie", "tv"] },
  { key: "scifi", label: "Sci-Fi & Fantasy", types: ["movie", "tv"] },
  { key: "mystery", label: "Mystery & Thriller", types: ["movie", "tv"] },
  { key: "animation", label: "Animation", types: ["movie", "tv"] },
  { key: "family", label: "Family & Kids", types: ["movie", "tv"] },
  { key: "documentary", label: "Documentary", types: ["movie", "tv"] },
  { key: "horror", label: "Horror", types: ["movie"] },
  { key: "romance", label: "Romance", types: ["movie"] },
  { key: "reality", label: "Reality", types: ["tv"] },
];

/** The genres that mean something for the All / Movies / TV filter. */
export function genresFor(filter: MediaFilter): typeof GENRES {
  return filter === "movie" || filter === "tv" ? GENRES.filter((g) => g.types.includes(filter)) : GENRES;
}

/**
 * Brands within a service, keyed like the server's BROWSE_BRANDS. Disney+ carries
 * general entertainment that otherwise leads its lists. `types` are the ones the
 * server can pick the brand out for: Seerr filters TV by keyword or network only,
 * so Pixar, Star Wars (Lucasfilm) and Nat Geo are films only.
 */
export const BRANDS: ReadonlyArray<{ key: string; label: string; service: string; types: ReadonlyArray<MediaType> }> = [
  { key: "disney", label: "Disney", service: "disney", types: ["movie", "tv"] },
  { key: "pixar", label: "Pixar", service: "disney", types: ["movie"] },
  { key: "marvel", label: "Marvel", service: "disney", types: ["movie", "tv"] },
  { key: "starwars", label: "Star Wars", service: "disney", types: ["movie"] },
  { key: "natgeo", label: "Nat Geo", service: "disney", types: ["movie"] },
];

/** The service's brands; with TV picked, only those that have TV. */
export function brandsFor(service: string, filter: MediaFilter): typeof BRANDS {
  return BRANDS.filter((b) => b.service === service && (filter !== "tv" || b.types.includes("tv")));
}

export const STREAM_SORTS: ReadonlyArray<{ value: StreamSort; label: string }> = [
  { value: "popular", label: "Popular" },
  { value: "top_rated", label: "Top rated" },
  { value: "newest", label: "Newest" },
];

/** A Show more page added to the list; titles already there (TMDB pages can overlap as popularity shifts) are skipped. */
export function appendNew<T extends { media_type: string; tmdb_id: number }>(list: readonly T[], more: readonly T[]): T[] {
  const seen = new Set(list.map((r) => `${r.media_type}/${r.tmdb_id}`));
  return [...list, ...more.filter((r) => !seen.has(`${r.media_type}/${r.tmdb_id}`))];
}

/** The Downloaded list narrowed by what's typed in the search box. */
export function filterLibrary<T extends { title: string }>(items: readonly T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  return q ? items.filter((i) => i.title.toLowerCase().includes(q)) : [...items];
}

/**
 * Latest-wins guard for overlapping async calls: typing "dune" fires searches
 * for "du", "dun", "dune", and only the newest may update the card.
 */
export class Latest {
  private _seq = 0;

  next(): () => boolean {
    const mine = ++this._seq;
    return () => mine === this._seq;
  }
}
