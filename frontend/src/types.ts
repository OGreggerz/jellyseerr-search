export type MediaType = "movie" | "tv";
/** "downloaded" lists what the server already has instead of searching. */
export type MediaFilter = MediaType | "all" | "downloaded";
/** What the card lists while the search box is empty. */
export type Browse = "trending" | "popular";

export type MediaStatus =
  | "not_requested"
  | "unknown"
  | "pending"
  | "processing"
  | "partially_available"
  | "available"
  | "blacklisted"
  | "deleted";

/** One hit from jellyseerr_search/search (see api.normalize_result). */
export interface SearchResult {
  tmdb_id: number;
  media_type: MediaType;
  title: string;
  year: number | null;
  overview: string;
  poster_url: string | null;
  status: MediaStatus;
}

export interface Season {
  season_number: number;
  name: string;
  episode_count: number;
  status: MediaStatus;
}

/** jellyseerr_search/episodes: what Sonarr has of each episode. */
export type EpisodeStatus = "downloaded" | "downloading" | "wanted" | "not_aired" | "missing";

export interface Episode {
  id: number;
  episode_number: number;
  title: string;
  air_date: string | null;
  status: EpisodeStatus;
  monitored: boolean;
}

/** A show's settings in Sonarr, as the picker shows them. */
export interface SonarrShow {
  series_id: number;
  title: string;
  daily: boolean;
  follow_new: boolean;
}

export interface SeasonEpisodes extends SonarrShow {
  /** The picker added the show to Sonarr (unmonitored) to list its episodes. */
  added: boolean;
  season_number: number;
  episodes: Episode[];
}

export interface CardConfig {
  type: string;
  title?: string;
  media_type?: MediaFilter;
  config_entry_id?: string;
  show_4k?: boolean;
  /** Trending / popular titles while the search box is empty. Default on. */
  show_trending?: boolean;
  /** A Remove button on titles in the library. Deletes files. Default off. */
  show_remove?: boolean;
}
