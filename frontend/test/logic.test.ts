import { describe, expect, it } from "vitest";
import {
  Latest,
  SERVICES,
  appendNew,
  brandsFor,
  genresFor,
  servicesFor,
  factsLine,
  runtimeLabel,
  trailerEmbedUrl,
  streamChoices,
  airDateLabel,
  canRequestMore,
  episodeLabel,
  ago,
  airTime,
  checkSummary,
  filterLibrary,
  releaseLine,
  resultChips,
  waitingDetail,
  isRemovable,
  isRequestable,
  pickableEpisodes,
  requestableSeasons,
  statusLabel,
  audioLines,
  audioSwitchWarning,
  episodeAudioLabel,
  episodeDubLine,
  waitingLabel,
} from "../src/logic";
import type { AudioState, DubInfo, Episode, Season, WaitingItem } from "../src/types";

const season = (n: number, status: Season["status"]): Season => ({
  season_number: n,
  name: `Season ${n}`,
  episode_count: 10,
  status,
});

describe("status", () => {
  it("only unrequested, unknown and deleted media are requestable", () => {
    expect(isRequestable("not_requested")).toBe(true);
    expect(isRequestable("deleted")).toBe(true);
    expect(isRequestable("pending")).toBe(false);
    expect(isRequestable("available")).toBe(false);
  });

  it("partially available shows can request more seasons", () => {
    expect(canRequestMore("partially_available")).toBe(true);
    expect(canRequestMore("available")).toBe(false);
  });

  it("hides chips for statuses that mean nothing to the user", () => {
    expect(statusLabel("not_requested")).toBeNull();
    expect(statusLabel("unknown")).toBeNull();
    expect(statusLabel("pending")).toBe("Requested");
  });
});

describe("requestableSeasons", () => {
  it("skips seasons already on the server or requested", () => {
    const seasons = [season(1, "available"), season(2, "pending"), season(3, "not_requested"), season(4, "deleted")];
    expect(requestableSeasons(seasons)).toEqual([3, 4]);
  });
});

describe("Latest", () => {
  it("only the newest call is current", () => {
    const latest = new Latest();
    const first = latest.next();
    const second = latest.next();
    expect(first()).toBe(false);
    expect(second()).toBe(true);
  });
});

describe("remove", () => {
  it("is offered only for titles Radarr/Sonarr hold", () => {
    expect(isRemovable("available")).toBe(true);
    expect(isRemovable("partially_available")).toBe(true);
    expect(isRemovable("processing")).toBe(true);
    for (const s of ["not_requested", "pending", "deleted", "unknown", "blacklisted"] as const) {
      expect(isRemovable(s)).toBe(false);
    }
  });
});

const episode = (id: number, status: Episode["status"], monitored = false): Episode => ({
  id,
  episode_number: id,
  title: `Episode ${id}`,
  air_date: "2026-11-04",
  status,
  monitored,
});

describe("episode picker", () => {
  it("only offers episodes that aren't on disk, on the way or already wanted", () => {
    const eps = [
      episode(1, "downloaded", true),
      episode(2, "downloading", true),
      episode(3, "wanted", true),
      episode(4, "missing"),
      episode(5, "not_aired"),
      episode(6, "not_aired", true),
    ];
    expect(pickableEpisodes(eps)).toEqual([4, 5]);
  });

  it("labels upcoming episodes by whether they will download", () => {
    expect(episodeLabel(episode(1, "not_aired", true))).toBe("When it airs");
    expect(episodeLabel(episode(1, "not_aired"))).toBe("Not aired");
    expect(episodeLabel(episode(1, "missing"))).toBeNull();
    expect(episodeLabel(episode(1, "wanted", true))).toBe("Not found yet");
  });

  it("formats air dates without a time zone shift", () => {
    expect(airDateLabel("2026-11-04")).toBe("4 Nov 2026");
    expect(airDateLabel(null)).toBe("No air date");
  });
});

describe("downloaded list", () => {
  it("narrows by title, ignoring case and spaces around the query", () => {
    const items = [{ title: "The Chase" }, { title: "The Celebrity Traitors" }, { title: "Dune" }];
    expect(filterLibrary(items, "  the c ").map((i) => i.title)).toEqual(["The Chase", "The Celebrity Traitors"]);
    expect(filterLibrary(items, "")).toHaveLength(3);
  });
});

const film = (over: Partial<WaitingItem>): WaitingItem => ({
  media_type: "movie", tmdb_id: 1, arr_id: 1, title: "Film", year: 2026, poster_url: null, state: "not_out", ...over,
});

describe("waiting list", () => {
  const now = new Date("2026-10-23T10:00:00Z");

  it("explains a cinema-only film", () => {
    const ali = film({ release_status: "inCinemas", in_cinemas: "2026-10-22", expected: "2027-01-20", expected_basis: "cinema_plus_90" });
    expect(waitingDetail(ali, now)).toBe(
      "In cinemas from 22 Oct 2026 · no home release date yet (counted as out around 20 Jan 2027)",
    );
  });

  it("gives the digital date when there is one, and says when nothing is dated", () => {
    expect(waitingDetail(film({ expected: "2026-12-12", expected_basis: "digital" }), now)).toBe("Digital release 12 Dec 2026");
    expect(waitingDetail(film({ release_status: "announced" }), now)).toBe("Announced · no release date yet");
  });

  it("says when a released film was last searched for", () => {
    const out = film({ state: "not_found", digital_release: "2026-10-01", last_search: "2026-10-23T07:00:00Z" });
    expect(waitingDetail(out, now)).toBe("Out since 1 Oct 2026 · last searched 3 hours ago");
  });

  it("gives a show's next episode", () => {
    const show = film({
      media_type: "tv",
      next_episode: { season: 3, episode: 5, title: "", air_date_utc: "2026-10-30T14:00:00Z" },
    });
    expect(waitingDetail(show, now)).toMatch(/^Next: S3E5 Fri 30 Oct, \d\d:00$/);
  });

  it("formats times and ages", () => {
    expect(airTime("2026-10-23T14:00:00Z", now)).toMatch(/^today \d\d:00$/);
    expect(ago("2026-10-21T10:00:00Z", now)).toBe("2 days ago");
  });

  it("summarises an indexer check", () => {
    const base = { checked_at: "", episode: null, best: null };
    expect(checkSummary({ ...base, found: 0, accepted: 0, reasons: [] })).toBe("Nothing posted yet.");
    expect(checkSummary({ ...base, found: 3, accepted: 0, reasons: ["CAM is not wanted in profile"] })).toBe(
      "3 copies found, none your profile accepts (CAM is not wanted in profile).",
    );
    expect(checkSummary({ ...base, found: 2, accepted: 1, best: "Film.2026.1080p.WEB", reasons: [] })).toBe(
      "1 suitable copy found: Film.2026.1080p.WEB.",
    );
  });
});

describe("release line", () => {
  const today = "2026-10-23";
  it("covers each film case", () => {
    expect(releaseLine({ tmdb_status: "Released", theatrical: "2026-10-22" }, "movie", today)).toBe(
      "In cinemas from 22 Oct 2026 · no digital release date yet",
    );
    expect(releaseLine({ tmdb_status: "Released", theatrical: "2026-10-22", digital: "2026-12-12" }, "movie", today)).toBe(
      "Digital release 12 Dec 2026",
    );
    expect(releaseLine({ tmdb_status: "Released", digital: "2026-10-06" }, "movie", today)).toBe(
      "Out to buy or stream since 6 Oct 2026",
    );
    expect(releaseLine({ tmdb_status: "In Production" }, "movie", today)).toBe("Not released yet (in production)");
  });
  it("covers shows", () => {
    expect(releaseLine({ tmdb_status: "Returning Series", next_air_date: "2026-10-30" }, "tv", today)).toBe("Next episode 30 Oct 2026");
    expect(releaseLine({ tmdb_status: "Ended", last_air_date: "2019-03-19" }, "tv", today)).toBe("Ended · last aired 19 Mar 2019");
  });
});

describe("result chips", () => {
  const r = (over: object) => ({ tmdb_id: 1, media_type: "tv", title: "T", year: 2023, overview: "", poster_url: null, status: "not_requested", ...over }) as any;
  it("shows both for a part-downloaded show waiting for more", () => {
    expect(resultChips(r({ arr: { downloaded: true, waiting: true } })).map((c) => c.label)).toEqual(["Downloaded", "Waiting"]);
  });
  it("shows Waiting for a followed show with nothing yet, which Jellyseerr calls not requested", () => {
    expect(resultChips(r({ arr: { downloaded: false, waiting: true } })).map((c) => c.label)).toEqual(["Waiting"]);
  });
  it("falls back to Jellyseerr's status", () => {
    expect(resultChips(r({ status: "pending" })).map((c) => c.label)).toEqual(["Requested"]);
    expect(resultChips(r({}))).toEqual([]);
  });
});

describe("anime audio", () => {
  const ep = (n: number, audio: Episode["audio"], english_subs = false): Episode => ({
    id: n, episode_number: n, title: "", air_date: "2026-10-02", status: audio ? "downloaded" : "wanted",
    monitored: true, audio, english_subs,
  });
  const dub: DubInfo = {
    episode: 3, date_utc: "2026-10-30T15:00:00Z", delayed: false, last_episode: 2, total: 12,
    source: "AnimeSchedule.net", url: "https://animeschedule.net/anime/x",
  };
  const now = new Date("2026-10-26T12:00:00Z");

  it("labels each file's audio", () => {
    expect(episodeAudioLabel(ep(1, "dual"))).toBe("Dual audio");
    expect(episodeAudioLabel(ep(1, "dub"))).toBe("Dub");
    expect(episodeAudioLabel(ep(1, "sub", true))).toBe("Sub · Eng subs");
    expect(episodeAudioLabel(ep(1, "sub"))).toBe("Sub");
    expect(episodeAudioLabel(ep(1, null))).toBeNull();
  });

  it("a wanted episode on dub only is waiting for its dub", () => {
    expect(episodeLabel(ep(4, null), "dub_only")).toBe("Waiting for dub");
    expect(episodeLabel(ep(4, null), "dub")).toBe("Not found yet");
  });

  it("dates each episode's dub from the next one, weekly", () => {
    expect(episodeDubLine(ep(3, "sub"), dub, true, now)).toMatch(/^Dub Fri 30 Oct, \d\d:00$/);
    expect(episodeDubLine(ep(5, null), dub, true, now)).toBe("Dub expected around 13 Nov");
    expect(episodeDubLine(ep(2, "sub"), dub, true, now)).toBeNull(); // before the next dub
    expect(episodeDubLine(ep(4, "dual"), dub, true, now)).toBeNull(); // already English
    expect(episodeDubLine(ep(4, "sub"), dub, false, now)).toBeNull(); // not the airing season
  });

  it("says what's downloaded in English and when the next dub is", () => {
    const state: AudioState = {
      available: true, anime: true, audio: "dub_only", in_arr: true, files: 4, english_files: 2,
      summary: "part_dub", dub_wanted: 2, dub, dub_dates: true,
    };
    const lines = audioLines(state, "tv", now);
    expect(lines[0]).toBe("2 of 4 downloaded episodes have English audio.");
    expect(lines[1]).toMatch(/^English dub: episode 3 Fri 30 Oct, \d\d:00 · dubbed up to episode 2$/);
    expect(audioLines({ ...state, dub: null }, "tv", now)[1]).toBe("No English dub dates listed for the next 4 weeks.");
    expect(audioLines({ ...state, dub: null, dub_dates: false, files: 0 }, "tv", now)).toEqual([]);
  });

  it("warns before switching", () => {
    expect(audioSwitchWarning("sub", "tv")).toMatch(/swapped for Japanese/);
    expect(audioSwitchWarning("dub_only", "tv")).toMatch(/downloads again/);
  });

  it("puts dub and sub chips on results", () => {
    const r = { tmdb_id: 1, media_type: "tv", title: "", year: null, overview: "", poster_url: null, status: "available" } as const;
    expect(resultChips({ ...r, arr: { downloaded: true, waiting: true, audio: "part_dub" } }).map((c) => c.label)).toEqual([
      "Downloaded", "Waiting", "Part dub",
    ]);
  });

  it("waiting for a dub", () => {
    const item: WaitingItem = {
      media_type: "tv", tmdb_id: 1, arr_id: 16, title: "The Apothecary Diaries", year: 2023, poster_url: null,
      state: "dub_wanted", audio: "dub", dub_wanted: 2, next_dub: dub,
    };
    expect(waitingLabel(item)).toBe("Waiting for dub");
    expect(waitingDetail(item, now)).toMatch(/^2 episodes in Japanese, dub wanted · Next dub: E3 Fri 30 Oct, \d\d:00$/);
    expect(waitingLabel({ ...item, state: "not_found", audio: "dub_only", missing: 1 })).toBe("Waiting for dub");
  });
});

describe("title screen extras", () => {
  it("writes lengths the short way", () => {
    expect([runtimeLabel(105), runtimeLabel(45), runtimeLabel(120)]).toEqual(["1h 45m", "45m", "2h"]);
  });

  it("puts length or seasons, genres and the rating on one line", () => {
    const base = { tmdb_status: "Released" };
    expect(factsLine({ ...base, runtime: 105, genres: ["Family", "Animation", "Music", "Adventure"], rating: 8.2 }, "movie"))
      .toBe("1h 45m \u00b7 Family, Animation, Music \u00b7 \u2605 8.2");
    expect(factsLine({ ...base, seasons_count: 3, runtime: 24, genres: ["Animation"], rating: null }, "tv"))
      .toBe("3 seasons \u00b7 24m episodes \u00b7 Animation");
    expect(factsLine({ ...base, seasons_count: 1 }, "tv")).toBe("1 season");
    // An older integration sends none of these.
    expect(factsLine(base, "movie")).toBeNull();
  });

  it("embeds the trailer without cookies, playing on tap", () => {
    expect(trailerEmbedUrl("Rvr68u6k5sI")).toBe(
      "https://www.youtube-nocookie.com/embed/Rvr68u6k5sI?autoplay=1&rel=0&playsinline=1",
    );
  });
});

describe("streaming browse", () => {
  it("offers every service unless the card picks some, in the card's order", () => {
    expect(servicesFor().map((s) => s.label).slice(0, 3)).toEqual(["Netflix", "Disney+", "Crunchyroll"]);
    expect(servicesFor([]).length).toBe(SERVICES.length);
    expect(servicesFor(["crunchyroll", "netflix"]).map((s) => s.id)).toEqual([283, 8]);
  });

  it("puts All first, covering every service on the card, unless there's only one", () => {
    const choices = streamChoices(["netflix", "disney"]);
    expect(choices.map((c) => c.key)).toEqual(["all", "netflix", "disney"]);
    expect(choices[0].ids).toEqual([8, 337]);
    expect(streamChoices()[0].ids.length).toBe(SERVICES.length);
    expect(streamChoices(["crunchyroll"]).map((c) => c.key)).toEqual(["crunchyroll"]);
  });

  it("ignores services it doesn't know, falling back to all when none are left", () => {
    expect(servicesFor(["netflix", "hulu"]).map((s) => s.key)).toEqual(["netflix"]);
    expect(servicesFor(["hulu"]).length).toBe(SERVICES.length);
  });

  it("only offers genres the filter has", () => {
    const keys = (f: Parameters<typeof genresFor>[0]) => genresFor(f).map((g) => g.key);
    expect(keys("all")).toContain("horror");
    expect(keys("all")).toContain("reality");
    expect(keys("tv")).not.toContain("horror");
    expect(keys("movie")).not.toContain("reality");
  });

  it("offers brands only for their service, and only TV-capable ones for TV", () => {
    expect(brandsFor("netflix", "all")).toEqual([]);
    expect(brandsFor("disney", "all").map((b) => b.label)).toEqual(["Disney", "Pixar", "Marvel", "Star Wars", "Nat Geo"]);
    expect(brandsFor("disney", "tv").map((b) => b.key)).toEqual(["disney", "marvel"]);
    expect(brandsFor("disney", "movie").length).toBe(5);
  });

  it("adds a Show more page without repeating titles already listed", () => {
    const t = (id: number, media_type: "movie" | "tv" = "tv") => ({ tmdb_id: id, media_type });
    expect(appendNew([t(1), t(2)], [t(2), t(3), t(2, "movie")])).toEqual([t(1), t(2), t(3), t(2, "movie")]);
  });
});
