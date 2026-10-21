import { describe, expect, it } from "vitest";
import { Latest, canRequestMore, isRemovable, isRequestable, requestableSeasons, statusLabel } from "../src/logic";
import type { Season } from "../src/types";

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
