import { describe, expect, it } from "vitest";
import {
  Latest,
  airDateLabel,
  canRequestMore,
  episodeLabel,
  ago,
  airTime,
  checkSummary,
  filterLibrary,
  releaseLine,
  waitingDetail,
  isRemovable,
  isRequestable,
  pickableEpisodes,
  requestableSeasons,
  statusLabel,
} from "../src/logic";
import type { Episode, Season, WaitingItem } from "../src/types";

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
