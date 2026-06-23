import { describe, it, expect } from "vitest";
import {
  startOfMonth,
  addMonths,
  addDays,
  addWeeks,
  startOfWeek,
  weekDays,
  buildMonthMatrix,
  dayKey,
  isSameDay,
  isSameMonth,
  eventSegmentsByDay,
  dayEventLayout,
  packEventColumns,
} from "../utils/calendar.js";

describe("startOfMonth", () => {
  it("returns the first day of the month", () => {
    expect(dayKey(startOfMonth(new Date(2026, 6, 17)))).toBe("2026-07-01");
  });
});

describe("addMonths", () => {
  it("moves forward across a year boundary", () => {
    expect(dayKey(addMonths(new Date(2026, 11, 1), 1))).toBe("2027-01-01");
  });

  it("moves backward", () => {
    expect(dayKey(addMonths(new Date(2026, 0, 1), -1))).toBe("2025-12-01");
  });
});

describe("buildMonthMatrix", () => {
  it("returns 42 days", () => {
    expect(buildMonthMatrix(new Date(2026, 6, 1))).toHaveLength(42);
  });

  it("starts on the Monday on or before the 1st", () => {
    // July 2026: the 1st is a Wednesday, so the grid starts Mon Jun 29.
    const days = buildMonthMatrix(new Date(2026, 6, 1));
    expect(days[0].getDay()).toBe(1); // Monday
    expect(dayKey(days[0])).toBe("2026-06-29");
  });

  it("contains every day of the target month", () => {
    const days = buildMonthMatrix(new Date(2026, 6, 1));
    const keys = days.map(dayKey);
    expect(keys).toContain("2026-07-01");
    expect(keys).toContain("2026-07-31");
  });
});

describe("isSameDay / isSameMonth", () => {
  it("compares days ignoring time", () => {
    expect(isSameDay(new Date(2026, 6, 1, 9), new Date(2026, 6, 1, 23))).toBe(true);
    expect(isSameDay(new Date(2026, 6, 1), new Date(2026, 6, 2))).toBe(false);
  });

  it("checks month membership", () => {
    expect(isSameMonth(new Date(2026, 6, 31), new Date(2026, 6, 1))).toBe(true);
    expect(isSameMonth(new Date(2026, 7, 1), new Date(2026, 6, 1))).toBe(false);
  });
});

describe("eventSegmentsByDay", () => {
  // Mon Mar 2 .. Sun Mar 8 2026 (local).
  const week = Array.from({ length: 7 }, (_, i) => new Date(2026, 2, 2 + i));

  it("places a single-day event only on its start day", () => {
    const ev = { id: 1, start: new Date(2026, 2, 3, 9) };
    const map = eventSegmentsByDay([ev], week);
    expect(Object.keys(map)).toEqual(["2026-03-03"]);
    expect(map["2026-03-03"][0]).toMatchObject({ isStart: true, isEnd: true });
  });

  it("spans every day a multi-day event covers, flagging start and end", () => {
    const ev = { id: 2, start: new Date(2026, 2, 3, 9), end: new Date(2026, 2, 5, 11) };
    const map = eventSegmentsByDay([ev], week);
    expect(Object.keys(map).sort()).toEqual([
      "2026-03-03",
      "2026-03-04",
      "2026-03-05",
    ]);
    expect(map["2026-03-03"][0]).toMatchObject({ isStart: true, isEnd: false });
    expect(map["2026-03-04"][0]).toMatchObject({ isStart: false, isEnd: false });
    expect(map["2026-03-05"][0]).toMatchObject({ isStart: false, isEnd: true });
  });

  it("clamps to the provided grid days", () => {
    const ev = { id: 3, start: new Date(2026, 1, 28), end: new Date(2026, 2, 3) };
    const map = eventSegmentsByDay([ev], week);
    // Only Mar 2 and Mar 3 are within the week grid.
    expect(Object.keys(map).sort()).toEqual(["2026-03-02", "2026-03-03"]);
    expect(map["2026-03-02"][0].isStart).toBe(false); // started before the grid
    expect(map["2026-03-03"][0].isEnd).toBe(true);
  });
});

describe("week helpers", () => {
  it("startOfWeek returns the Monday of the week", () => {
    // 2026-03-04 is a Wednesday.
    expect(dayKey(startOfWeek(new Date(2026, 2, 4)))).toBe("2026-03-02");
  });

  it("weekDays returns Mon→Sun", () => {
    const days = weekDays(new Date(2026, 2, 4));
    expect(days.map(dayKey)).toEqual([
      "2026-03-02",
      "2026-03-03",
      "2026-03-04",
      "2026-03-05",
      "2026-03-06",
      "2026-03-07",
      "2026-03-08",
    ]);
  });

  it("addDays / addWeeks shift correctly", () => {
    expect(dayKey(addDays(new Date(2026, 2, 4), 5))).toBe("2026-03-09");
    expect(dayKey(addWeeks(new Date(2026, 2, 4), -1))).toBe("2026-02-25");
  });
});

describe("packEventColumns", () => {
  it("places non-overlapping segments in a single column", () => {
    const out = packEventColumns([
      { startMin: 60, endMin: 120 },
      { startMin: 180, endMin: 240 },
    ]);
    expect(out.every((s) => s.cols === 1 && s.col === 0)).toBe(true);
  });

  it("splits two overlapping segments into two columns", () => {
    const out = packEventColumns([
      { startMin: 60, endMin: 180 },
      { startMin: 120, endMin: 240 },
    ]);
    expect(out.map((s) => s.cols)).toEqual([2, 2]);
    expect(new Set(out.map((s) => s.col))).toEqual(new Set([0, 1]));
  });

  it("reuses a column once an earlier segment has ended", () => {
    const out = packEventColumns([
      { startMin: 0, endMin: 60 },
      { startMin: 30, endMin: 90 },
      { startMin: 70, endMin: 120 }, // overlaps the 2nd but not the 1st
    ]);
    const byStart = Object.fromEntries(out.map((s) => [s.startMin, s]));
    expect(byStart[70].col).toBe(0); // free again after the first ended at 60
  });
});

describe("dayEventLayout", () => {
  const day = new Date(2026, 2, 4); // Wed

  it("separates all-day from timed events", () => {
    const events = [
      { id: 1, title: "Holiday", all_day: true, start: new Date(2026, 2, 4, 0) },
      {
        id: 2,
        title: "Call",
        all_day: false,
        start: new Date(2026, 2, 4, 9),
        end: new Date(2026, 2, 4, 10),
      },
    ];
    const { allDay, timed } = dayEventLayout(events, day);
    expect(allDay.map((e) => e.id)).toEqual([1]);
    expect(timed).toHaveLength(1);
    expect(timed[0]).toMatchObject({ startMin: 540, endMin: 600 });
  });

  it("treats an event spanning the whole day as all-day", () => {
    const events = [
      {
        id: 3,
        title: "Trip",
        start: new Date(2026, 2, 3, 8),
        end: new Date(2026, 2, 6, 8),
      },
    ];
    const { allDay, timed } = dayEventLayout(events, day);
    expect(allDay).toHaveLength(1);
    expect(timed).toHaveLength(0);
  });

  it("clips a timed event to the day and gives open-ended ones an hour", () => {
    const events = [
      { id: 4, title: "Open", start: new Date(2026, 2, 4, 23), end: null },
    ];
    const { timed } = dayEventLayout(events, day);
    expect(timed[0].startMin).toBe(1380); // 23:00
    expect(timed[0].endMin).toBe(1440); // clipped to midnight
  });
});
