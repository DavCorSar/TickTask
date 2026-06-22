import { describe, it, expect } from "vitest";
import {
  startOfMonth,
  addMonths,
  buildMonthMatrix,
  dayKey,
  isSameDay,
  isSameMonth,
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
