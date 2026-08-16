import { describe, it, expect } from "vitest";
import { entriesToCsv } from "../utils/csv.js";
import { formatClock } from "../utils/time.js";

describe("entriesToCsv", () => {
  it("returns just the header for an empty list", () => {
    expect(entriesToCsv([])).toBe("Date,Start,End,Duration,Task,Subtask,Deleted");
  });

  it("formats a closed entry as a full row", () => {
    const csv = entriesToCsv([
      {
        clock_in: "2026-06-22T09:00:00",
        clock_out: "2026-06-22T10:30:00",
        durationMs: 90 * 60 * 1000,
        task_name: "Website",
        subtask_name: "Homepage",
        deleted: false,
      },
    ]);
    const lines = csv.split("\r\n");
    expect(lines).toHaveLength(2);
    const start = formatClock("2026-06-22T09:00:00");
    const end = formatClock("2026-06-22T10:30:00");
    expect(lines[1]).toBe(`2026-06-22,${start},${end},01:30:00,Website,Homepage,no`);
  });

  it("leaves the end column blank for an entry still clocked in", () => {
    const csv = entriesToCsv([
      {
        clock_in: "2026-06-22T09:00:00",
        clock_out: null,
        durationMs: 0,
        task_name: "Website",
        subtask_name: "Homepage",
        deleted: false,
      },
    ]);
    const [, row] = csv.split("\r\n");
    const [, , end] = row.split(",");
    expect(end).toBe("");
  });

  it("marks soft-deleted entries", () => {
    const csv = entriesToCsv([
      {
        clock_in: "2026-06-22T09:00:00",
        clock_out: "2026-06-22T09:30:00",
        durationMs: 30 * 60 * 1000,
        task_name: "Website",
        subtask_name: "Homepage",
        deleted: true,
      },
    ]);
    expect(csv.split("\r\n")[1].endsWith(",yes")).toBe(true);
  });

  it("quotes and escapes fields containing commas or quotes", () => {
    const csv = entriesToCsv([
      {
        clock_in: "2026-06-22T09:00:00",
        clock_out: "2026-06-22T09:30:00",
        durationMs: 30 * 60 * 1000,
        task_name: 'Q3, "Launch"',
        subtask_name: "Homepage",
        deleted: false,
      },
    ]);
    const [, row] = csv.split("\r\n");
    expect(row).toContain('"Q3, ""Launch"""');
  });
});
