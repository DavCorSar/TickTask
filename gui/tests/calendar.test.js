import { describe, it, expect } from "vitest";
import {
  startOfMonth,
  addMonths,
  buildMonthMatrix,
  dayKey,
  isSameDay,
  isSameMonth,
  eventSegmentsByDay,
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
