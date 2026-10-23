// Pure helpers, kept out of the card so vitest can cover them without a DOM.

import type { Episode, MediaStatus, Season } from "./types";

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
