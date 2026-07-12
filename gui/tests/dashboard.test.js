import { describe, it, expect } from "vitest";
import {
  formatHours,
  rangeForBucket,
  rangeForDays,
  toDateInput,
  formatBucketLabel,
  chartColor,
  niceCeil,
  stackedBuckets,
  donutSegments,
  heatmapLevel,
  heatmapGrid,
  BUCKET_OPTIONS,
  RANGE_OPTIONS,
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

describe("rangeForDays", () => {
  it("returns a trailing window of the given length starting at midnight", () => {
    const now = new Date(2026, 5, 22, 14, 30); // 2026-06-22 14:30 local
    const { start, end } = rangeForDays(7, now);
    expect(end).toEqual(now);
    expect(start.getHours()).toBe(0);
    expect(start.getMinutes()).toBe(0);
    // 7 days before the 22nd of June is the 15th.
    expect(start.getMonth()).toBe(5);
    expect(start.getDate()).toBe(15);
  });

  it("backs rangeForBucket with each bucket's window length", () => {
    const now = new Date(2026, 5, 22);
    for (const option of BUCKET_OPTIONS) {
      expect(rangeForBucket(option.value, now)).toEqual(
        rangeForDays(option.days, now),
      );
    }
  });

  it("offers 7 / 30 / 90 day presets", () => {
    expect(RANGE_OPTIONS.map((o) => o.value)).toEqual([7, 30, 90]);
  });
});

describe("toDateInput", () => {
  it("formats a date as a zero-padded local YYYY-MM-DD", () => {
    expect(toDateInput(new Date(2026, 2, 9))).toBe("2026-03-09");
  });

  it("uses local components, not UTC", () => {
    // Late-evening local time can be the next day in UTC; the label must not drift.
    const date = new Date(2026, 0, 31, 23, 30);
    expect(toDateInput(date)).toBe("2026-01-31");
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

describe("stackedBuckets", () => {
  const buckets = [{ period_start: "2026-01-01" }, { period_start: "2026-01-02" }];
  const tasks = [
    { task_id: 1, task_name: "A", deleted: false, series: [2, 0] },
    { task_id: 2, task_name: "B", deleted: false, series: [1, 3] },
  ];

  it("stacks per-task hours into each bucket and totals them", () => {
    const stacks = stackedBuckets(buckets, tasks);
    expect(stacks).toHaveLength(2);
    expect(stacks[0].total).toBe(3);
    expect(stacks[1].total).toBe(3);
    expect(stacks[0].segments.map((s) => s.name)).toEqual(["A", "B"]);
  });

  it("drops zero-hour segments", () => {
    const stacks = stackedBuckets(buckets, tasks);
    // Task A has 0 on the second day, so only B remains there.
    expect(stacks[1].segments.map((s) => s.name)).toEqual(["B"]);
  });

  it("keeps each task's palette color by its index", () => {
    const stacks = stackedBuckets(buckets, tasks);
    expect(stacks[0].segments[0].color).toBe(chartColor(0));
    expect(stacks[0].segments[1].color).toBe(chartColor(1));
  });
});

describe("donutSegments", () => {
  const tasks = [
    { task_id: 1, task_name: "A", deleted: false, hours: 1 },
    { task_id: 2, task_name: "B", deleted: false, hours: 3 },
    { task_id: 3, task_name: "C", deleted: false, hours: 0 },
  ];

  it("computes share, sorted biggest first, dropping empty tasks", () => {
    const { total, segments } = donutSegments(tasks);
    expect(total).toBe(4);
    expect(segments.map((s) => s.name)).toEqual(["B", "A"]);
    expect(segments[0].percent).toBe(75);
    expect(segments[1].percent).toBe(25);
  });

  it("returns fractions and cumulative offsets that tile the ring", () => {
    const { segments } = donutSegments(tasks);
    expect(segments[0].offset).toBe(0);
    expect(segments[0].fraction).toBeCloseTo(0.75);
    expect(segments[1].offset).toBeCloseTo(0.75);
    const last = segments[segments.length - 1];
    expect(last.offset + last.fraction).toBeCloseTo(1);
  });

  it("keeps each task's palette color by its original index", () => {
    const { segments } = donutSegments(tasks);
    // B is task index 1, A is index 0, even after sorting.
    expect(segments[0].color).toBe(chartColor(1));
    expect(segments[1].color).toBe(chartColor(0));
  });

  it("handles an all-empty set", () => {
    const { total, segments } = donutSegments([
      { task_id: 1, task_name: "A", hours: 0 },
    ]);
    expect(total).toBe(0);
    expect(segments).toEqual([]);
  });
});

describe("heatmapLevel", () => {
  it("is 0 for no hours or no max", () => {
    expect(heatmapLevel(0, 5)).toBe(0);
    expect(heatmapLevel(3, 0)).toBe(0);
  });

  it("buckets into 1–4 by quartile of the max", () => {
    expect(heatmapLevel(1, 8)).toBe(1);
    expect(heatmapLevel(4, 8)).toBe(2);
    expect(heatmapLevel(8, 8)).toBe(4);
  });
});

describe("heatmapGrid", () => {
  it("lays out `weeks` Monday-started columns ending on the week of `end`", () => {
    const end = new Date(2026, 5, 17); // Wed 2026-06-17
    const { columns } = heatmapGrid([], { weeks: 4, end });
    expect(columns).toHaveLength(4);
    columns.forEach((col) => expect(col).toHaveLength(7));
    // First cell of the last column is the Monday of end's week (2026-06-15).
    expect(columns[3][0].date).toBe("2026-06-15");
  });

  it("maps hours onto the right day and flags future cells", () => {
    const end = new Date(2026, 5, 17);
    const { columns, max } = heatmapGrid(
      [{ period_start: "2026-06-15", hours: 5 }],
      { weeks: 1, end },
    );
    expect(max).toBe(5);
    expect(columns[0][0].hours).toBe(5);
    expect(columns[0][0].level).toBe(4);
    // Thu–Sun of that week are after Wed the 17th → future.
    expect(columns[0][3].future).toBe(true);
    expect(columns[0][0].future).toBe(false);
  });
});
