// Pure CSV-building helpers, kept framework-free so they're easy to unit test.
// Auto-imported across the app by Nuxt (utils/ directory).

import { formatClock, formatDuration } from "./time.js";

function escapeCsvField(value) {
  const str = String(value ?? "");
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Build a CSV string of tracked time entries, one row per entry.
 * Each entry must carry a `durationMs` field precomputed by the caller —
 * open entries (no `clock_out`) measure against "now", which this function
 * has no business knowing about.
 */
export function entriesToCsv(entries) {
  const header = ["Date", "Start", "End", "Duration", "Task", "Subtask", "Deleted"];
  const rows = entries.map((entry) => {
    const row = [
      new Date(entry.clock_in).toLocaleDateString("en-CA"), // YYYY-MM-DD, unambiguous
      formatClock(entry.clock_in),
      entry.clock_out ? formatClock(entry.clock_out) : "",
      formatDuration(entry.durationMs),
      entry.task_name,
      entry.subtask_name,
      entry.deleted ? "yes" : "no",
    ];
    return row.map(escapeCsvField).join(",");
  });
  return [header.join(","), ...rows].join("\r\n");
}
