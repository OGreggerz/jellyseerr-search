// Pure helpers, kept out of the card so vitest can cover them without a DOM.

import type { CheckResult, Episode, MediaStatus, ReleaseInfo, SearchResult, Season, WaitingItem } from "./types";

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

/** Chip text for an episode, or null for one that can still be picked. */
export function episodeLabel(ep: Episode): string | null {
  switch (ep.status) {
    case "downloaded":
      return "Downloaded";
    case "downloading":
      return "Downloading";
    case "wanted":
      return "Not found yet";
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
  return { downloading: "Downloading", not_found: "Not found yet", not_out: "Not out yet" }[item.state];
}

/** The line under a Waiting title: when it's out, or what it's waiting for. */
export function waitingDetail(item: WaitingItem, now: Date = new Date()): string {
  if (item.state === "downloading") return "Downloading now.";
  if (item.media_type === "tv") {
    const parts: string[] = [];
    if (item.missing) parts.push(`${item.missing} episode${item.missing === 1 ? "" : "s"} out but not found yet`);
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
    return `${result.accepted} suitable cop${result.accepted === 1 ? "y" : "ies"} found${what}${result.best ? `: ${result.best}` : ""}.`;
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
