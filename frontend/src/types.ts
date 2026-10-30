export type MediaType = "movie" | "tv";
/** "downloaded" lists what the server already has; "waiting" what Sonarr/Radarr
 *  want but haven't got. Neither searches. */
export type MediaFilter = MediaType | "all" | "downloaded" | "waiting";

export type WaitingState = "downloading" | "not_found" | "not_out" | "dub_wanted";

/** Anime audio, chosen per title: dub preferred (Japanese now, the dub replaces
 *  it), dub only (wait for it), or Japanese with subtitles. */
export type AudioChoice = "dub" | "dub_only" | "sub";
/** A show's downloaded files: all in English, some, or none. */
export type AudioSummary = "dub" | "part_dub" | "sub_only";
/** One file's audio tracks. */
export type FileAudio = "dual" | "dub" | "sub";

/** The next English dub episode, from AnimeSchedule.net's timetable. */
export interface DubInfo {
  episode: number | null;
  date_utc: string | null;
  delayed: boolean;
  last_episode: number | null;
  total: number | null;
  source: string;
  url: string;
}

/** jellyseerr_search/audio: the page's audio section. */
export interface AudioState {
  /** Sonarr/Radarr has the three anime profiles. */
  available: boolean;
  anime: boolean;
  audio: AudioChoice | null;
  in_arr: boolean;
  files: number;
  english_files: number;
  summary: AudioSummary | null;
  dub_wanted: number;
  dub: DubInfo | null;
  /** Dub dates are set up (an AnimeSchedule token), so a missing date means none listed. */
  dub_dates: boolean;
}

/** jellyseerr_search/waiting: a wanted title not downloaded yet. */
export interface WaitingItem {
  media_type: MediaType;
  tmdb_id: number | null;
  arr_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
  state: WaitingState;
  last_search?: string | null;
  // Films
  release_status?: string | null;
  in_cinemas?: string | null;
  digital_release?: string | null;
  physical_release?: string | null;
  expected?: string | null;
  expected_basis?: "digital" | "physical" | "cinema_plus_90" | null;
  // Shows
  missing?: number;
  next_episode?: { season: number; episode: number; title: string; air_date_utc: string } | null;
  audio?: AudioChoice | null;
  /** Episodes it has, but not in English yet. */
  dub_wanted?: number;
  next_dub?: DubInfo | null;
}

/** jellyseerr_search/release: TMDB's dates, via Jellyseerr. */
export interface ReleaseInfo {
  tmdb_status: string | null;
  // Films
  theatrical?: string | null;
  digital?: string | null;
  physical?: string | null;
  // Shows
  next_air_date?: string | null;
  last_air_date?: string | null;
  // The title screen's extras (integration 0.16.0+; absent from older ones).
  /** Minutes: a film's length, a show's usual episode. */
  runtime?: number | null;
  seasons_count?: number | null;
  genres?: string[];
  /** TMDB's score out of 10, once enough people have voted. */
  rating?: number | null;
  tagline?: string | null;
  credit?: { label: string; names: string[] } | null;
  cast?: Array<{ name: string; character: string | null; photo_url: string | null }>;
  /** A YouTube video id and its title. */
  trailer?: { key: string; name: string } | null;
}

/** jellyseerr_search/waiting/check: what an interactive search found. */
export interface CheckResult {
  found: number;
  accepted: number;
  /** Of those accepted, how many have English audio. */
  dubbed?: number;
  best: string | null;
  reasons: string[];
  checked_at: string;
  episode: { season: number; episode: number } | null;
}
/** What the card lists while the search box is empty. */
export type Browse = "trending" | "popular" | "streaming";
/** How the Streaming list is ordered (the server's `sort`). */
export type StreamSort = "popular" | "top_rated" | "newest";

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
  /** What Sonarr/Radarr have of it, when set up: at least one file / wanted and
   *  not all here (both for a part-downloaded show waiting for more). */
  arr?: { downloaded: boolean; waiting: boolean; audio?: AudioSummary | null };
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
  audio?: FileAudio | null;
  english_subs?: boolean;
}

/** jellyseerr_search/seasons with Sonarr set up: the show page's follow state. */
export interface ShowState {
  in_sonarr: boolean;
  follow_new: boolean;
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
  /** Services the Streaming list offers, as SERVICES keys, in this order. Default: all. */
  services?: string[];
  /** Country whose streaming catalogues to show (two letters). Default GB. */
  region?: string;
}
