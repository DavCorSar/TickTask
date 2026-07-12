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
  return rangeForDays(option.days, now);
}

/** Trailing-window presets (in days) offered by the range selector. */
export const RANGE_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
];

/**
 * Returns the `{ start, end }` Date range for a trailing window of `days` days:
 * ending now and starting at midnight `days` days ago.
 */
export function rangeForDays(days, now = new Date()) {
  const start = new Date(now);
  start.setDate(start.getDate() - days);
  start.setHours(0, 0, 0, 0);
  return { start, end: new Date(now) };
}

/**
 * Formats a Date as a local `YYYY-MM-DD` string for a `<input type="date">`
 * (local, so the day never drifts the way `toISOString()` can).
 */
export function toDateInput(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
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

/**
 * Turns the time-series `buckets` + `by_task` response into per-bucket stacks:
 * one entry per bucket with its `total` and the `segments` (one per task with
 * time in that bucket, keeping the task's palette index so colors line up with
 * the trend chart). Zero-hour segments are dropped.
 */
export function stackedBuckets(buckets, tasks) {
  const stacks = buckets.map((b) => ({
    period_start: b.period_start,
    total: 0,
    segments: [],
  }));
  tasks.forEach((task, index) => {
    const color = chartColor(index);
    (task.series || []).forEach((hours, i) => {
      if (!stacks[i] || hours <= 0) return;
      stacks[i].segments.push({
        taskId: task.task_id,
        name: task.task_name,
        deleted: task.deleted,
        color,
        hours,
      });
      stacks[i].total += hours;
    });
  });
  return stacks;
}

/**
 * Turns the per-task totals (`by_task`) into donut segments: each task's share
 * of the total as a `fraction` (0–1) and cumulative `offset` (so a segment
 * spans `[offset, offset + fraction)` of the ring), plus a rounded `percent`.
 * Tasks with no time are dropped; the rest come biggest-first. Palette index is
 * the task's original position, so colors match the other charts.
 */
export function donutSegments(tasks) {
  const active = tasks
    .map((task, index) => ({
      taskId: task.task_id,
      name: task.task_name,
      deleted: task.deleted,
      color: chartColor(index),
      hours: task.hours,
    }))
    .filter((t) => t.hours > 0)
    .sort((a, b) => b.hours - a.hours);

  const total = active.reduce((sum, t) => sum + t.hours, 0);
  let offset = 0;
  const segments = active.map((t) => {
    const fraction = total ? t.hours / total : 0;
    const seg = {
      ...t,
      fraction,
      offset,
      percent: total ? Math.round((t.hours / total) * 1000) / 10 : 0,
    };
    offset += fraction;
    return seg;
  });
  return { total, segments };
}

/** Maps an hours value to a heatmap intensity level (0 = none, 1–4 = quartiles). */
export function heatmapLevel(hours, max) {
  if (!hours || hours <= 0 || max <= 0) return 0;
  return Math.min(4, Math.ceil((hours / max) * 4));
}

/**
 * Builds a GitHub-style day heatmap: `weeks` Monday-started columns of 7 days
 * ending on the week of `end`. Each cell carries its `date`, `hours`, intensity
 * `level` and a `future` flag (days after `end`). Also returns the observed
 * `max` and `monthLabels` (the column index where each month first appears).
 */
export function heatmapGrid(buckets, { weeks = 53, end = new Date() } = {}) {
  const byDate = new Map();
  let max = 0;
  for (const b of buckets) {
    byDate.set(b.period_start, b.hours);
    if (b.hours > max) max = b.hours;
  }

  const endDay = new Date(end);
  endDay.setHours(0, 0, 0, 0);
  // Monday (0) … Sunday (6) index of `end`, then walk back to the first column.
  const dow = (endDay.getDay() + 6) % 7;
  const firstMonday = new Date(endDay);
  firstMonday.setDate(firstMonday.getDate() - dow - (weeks - 1) * 7);

  const columns = [];
  const monthLabels = [];
  let lastMonth = -1;
  for (let w = 0; w < weeks; w++) {
    const days = [];
    for (let d = 0; d < 7; d++) {
      const date = new Date(firstMonday);
      date.setDate(date.getDate() + w * 7 + d);
      const key = toDateInput(date);
      const future = date > endDay;
      const hours = byDate.get(key) || 0;
      days.push({
        date: key,
        hours,
        future,
        level: future ? 0 : heatmapLevel(hours, max),
      });
    }
    if (days[0]) {
      const month = new Date(`${days[0].date}T00:00:00`).getMonth();
      if (month !== lastMonth) {
        lastMonth = month;
        monthLabels.push({
          week: w,
          text: new Date(`${days[0].date}T00:00:00`).toLocaleDateString([], {
            month: "short",
          }),
        });
      }
    }
    columns.push(days);
  }
  return { columns, max, monthLabels };
}
