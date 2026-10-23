import { describe, expect, it } from "vitest";
import {
  Latest,
  airDateLabel,
  canRequestMore,
  episodeLabel,
  filterLibrary,
  isRemovable,
  isRequestable,
  pickableEpisodes,
  requestableSeasons,
  statusLabel,
} from "../src/logic";
import type { Episode, Season } from "../src/types";

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
