export type MediaType = "movie" | "tv";
export type MediaFilter = MediaType | "all";

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

export interface CardConfig {
  type: string;
  title?: string;
  media_type?: MediaFilter;
  config_entry_id?: string;
  show_4k?: boolean;
  /** Trending titles while the search box is empty. Default on. */
  show_trending?: boolean;
}
