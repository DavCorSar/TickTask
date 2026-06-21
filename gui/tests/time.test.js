import { describe, it, expect } from "vitest";
import { formatDuration, formatClock } from "../utils/time.js";

describe("formatDuration", () => {
  it("formats zero", () => {
    expect(formatDuration(0)).toBe("00:00:00");
  });

  it("formats seconds only", () => {
    expect(formatDuration(5_000)).toBe("00:00:05");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(90_000)).toBe("00:01:30");
  });

  it("formats an exact hour", () => {
    expect(formatDuration(3_600_000)).toBe("01:00:00");
  });

  it("formats hours, minutes and seconds together", () => {
    // 2h 3m 4s
    expect(formatDuration((2 * 3600 + 3 * 60 + 4) * 1000)).toBe("02:03:04");
  });

  it("supports durations over 24 hours", () => {
    expect(formatDuration(25 * 3600 * 1000)).toBe("25:00:00");
  });

  it("truncates sub-second milliseconds", () => {
    expect(formatDuration(1_999)).toBe("00:00:01");
  });

  it("clamps negative values to zero", () => {
    expect(formatDuration(-5_000)).toBe("00:00:00");
  });
});

describe("formatClock", () => {
  it("returns a locale-agnostic hh:mm style string", () => {
    const result = formatClock(new Date("2026-06-22T09:05:00"));
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });

  it("accepts an ISO string as input", () => {
    expect(typeof formatClock("2026-06-22T09:05:00")).toBe("string");
  });
});
