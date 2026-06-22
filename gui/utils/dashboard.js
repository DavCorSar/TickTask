// Pure helpers for the dashboard view: hours formatting, chart geometry and
// the date ranges behind each bucket granularity. Kept framework-free so they
// are easy to unit test. Auto-imported across the app by Nuxt (utils/).

/**
 * Format decimal hours (e.g. 2.5) as a compact `Xh Ym` label.
 * 0 renders as `0h`; sub-hour values drop the hour part (`45m`).
 */
export function formatHours(hours) {
  const totalMinutes = Math.round((Number(hours) || 0) * 60);
  if (totalMinutes <= 0) return "0h";
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

/** Bucket granularities offered by the dashboard, each with its trailing window. */
export const BUCKET_OPTIONS = [
  { value: "day", label: "Daily", days: 30 },
  { value: "week", label: "Weekly", days: 7 * 12 },
  { value: "month", label: "Monthly", days: 365 },
];

/**
 * Returns the `{ start, end }` Date range to request for a given bucket: a
 * trailing window ending now and starting at midnight `days` ago.
 */
export function rangeForBucket(bucket, now = new Date()) {
  const option =
    BUCKET_OPTIONS.find((b) => b.value === bucket) || BUCKET_OPTIONS[0];
  const start = new Date(now);
  start.setDate(start.getDate() - option.days);
  start.setHours(0, 0, 0, 0);
  return { start, end: new Date(now) };
}

/**
 * Format a bucket's `period_start` (an ISO `YYYY-MM-DD` date) as a short axis
 * label. Parsed as local time so the label never drifts by a day.
 */
export function formatBucketLabel(periodStart, bucket) {
  const date = new Date(`${periodStart}T00:00:00`);
  if (bucket === "month") {
    return date.toLocaleDateString([], { month: "short", year: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

/** A small qualitative palette for the per-task bars, cycled by index. */
export const CHART_COLORS = [
  "#007CBF",
  "#5EA611",
  "#D30F4B",
  "#9333EA",
  "#F59E0B",
  "#0EA5E9",
  "#14B8A6",
  "#EC4899",
];

/** Returns a stable color for the chart series at position `index`. */
export function chartColor(index) {
  return CHART_COLORS[index % CHART_COLORS.length];
}

/**
 * Rounds a value up to a visually "nice" axis maximum (1, 2 or 5 times a power
 * of ten), so chart gridlines land on readable numbers. Always >= 1.
 */
export function niceCeil(value) {
  if (!value || value <= 0) return 1;
  const power = Math.pow(10, Math.floor(Math.log10(value)));
  const normalized = value / power;
  const nice =
    normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return nice * power;
}
