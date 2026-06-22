import { describe, it, expect } from "vitest";
import {
  formatHours,
  rangeForBucket,
  formatBucketLabel,
  chartColor,
  niceCeil,
  BUCKET_OPTIONS,
  CHART_COLORS,
} from "../utils/dashboard.js";

describe("formatHours", () => {
  it("renders zero and negatives as 0h", () => {
    expect(formatHours(0)).toBe("0h");
    expect(formatHours(-3)).toBe("0h");
    expect(formatHours(null)).toBe("0h");
  });

  it("combines hours and minutes", () => {
    expect(formatHours(2.5)).toBe("2h 30m");
  });

  it("drops the minutes part on whole hours", () => {
    expect(formatHours(3)).toBe("3h");
  });

  it("drops the hours part below one hour", () => {
    expect(formatHours(0.75)).toBe("45m");
  });

  it("rounds to the nearest minute", () => {
    expect(formatHours(1 / 60 + 0.0001)).toBe("1m");
  });
});

describe("rangeForBucket", () => {
  it("returns a trailing window starting at midnight days ago", () => {
    const now = new Date(2026, 5, 22, 14, 30); // 2026-06-22 14:30 local
    const { start, end } = rangeForBucket("day", now);
    expect(end).toEqual(now);
    expect(start.getHours()).toBe(0);
    expect(start.getMinutes()).toBe(0);
    // 30 days before the 22nd of June is the 23rd of May.
    expect(start.getMonth()).toBe(4);
    expect(start.getDate()).toBe(23);
  });

  it("uses a longer window for weekly and monthly buckets", () => {
    const now = new Date(2026, 5, 22);
    const days = (b) => Math.round((now - rangeForBucket(b, now).start) / 86400000);
    expect(days("week")).toBeGreaterThan(days("day"));
    expect(days("month")).toBeGreaterThan(days("week"));
  });

  it("falls back to the first bucket for an unknown value", () => {
    const now = new Date(2026, 5, 22);
    expect(rangeForBucket("nope", now)).toEqual(rangeForBucket(BUCKET_OPTIONS[0].value, now));
  });
});

describe("formatBucketLabel", () => {
  it("includes the day for day and week buckets", () => {
    expect(formatBucketLabel("2026-03-09", "day")).toMatch(/9/);
    expect(formatBucketLabel("2026-03-09", "week")).toMatch(/9/);
  });

  it("omits the day for month buckets", () => {
    expect(formatBucketLabel("2026-03-01", "month")).not.toMatch(/\b1\b/);
  });
});

describe("chartColor", () => {
  it("cycles through the palette", () => {
    expect(chartColor(0)).toBe(CHART_COLORS[0]);
    expect(chartColor(CHART_COLORS.length)).toBe(CHART_COLORS[0]);
  });
});

describe("niceCeil", () => {
  it("never returns less than one", () => {
    expect(niceCeil(0)).toBe(1);
    expect(niceCeil(-5)).toBe(1);
    expect(niceCeil(0.3)).toBe(0.5);
  });

  it("rounds up to 1, 2 or 5 times a power of ten", () => {
    expect(niceCeil(3.2)).toBe(5);
    expect(niceCeil(7)).toBe(10);
    expect(niceCeil(12)).toBe(20);
    expect(niceCeil(1)).toBe(1);
  });
});
