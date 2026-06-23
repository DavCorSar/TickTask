// Pure date helpers for the month calendar. Framework-free and easy to test.
// Auto-imported across the app by Nuxt (utils/ directory).

const pad = (n) => String(n).padStart(2, "0");

/** First day of the month for the given date. */
export function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/** Returns a new date shifted by `n` months (n can be negative). */
export function addMonths(date, n) {
  return new Date(date.getFullYear(), date.getMonth() + n, 1);
}

/** Returns a new date shifted by `n` days (n can be negative), at midnight. */
export function addDays(date, n) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + n);
}

/** Monday (00:00) of the week containing `date`. */
export function startOfWeek(date) {
  const offset = (date.getDay() + 6) % 7; // Monday = 0
  return addDays(date, -offset);
}

/** Returns a new date shifted by `n` weeks (n can be negative). */
export function addWeeks(date, n) {
  return addDays(date, n * 7);
}

/** The seven days (Mon→Sun) of the week containing `date`, each at midnight. */
export function weekDays(date) {
  const start = startOfWeek(date);
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

/**
 * Lays out a day's events for a time-grid (week/day) view. Splits them into
 * `allDay` (all-day events or ones covering the whole day) and `timed` segments
 * clipped to the day, each with `startMin`/`endMin` (minutes from midnight) and
 * a `col`/`cols` pair packing overlapping events side by side.
 */
export function dayEventLayout(events, day) {
  const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate());
  const dayEnd = addDays(dayStart, 1);
  const allDay = [];
  const raw = [];

  for (const event of events) {
    const start = new Date(event.start);
    const end = event.end
      ? new Date(event.end)
      : new Date(start.getTime() + 60 * 60000); // default 1h for open-ended
    if (end <= dayStart || start >= dayEnd) continue; // doesn't touch this day

    if (event.all_day || (start <= dayStart && end >= dayEnd)) {
      allDay.push(event);
      continue;
    }

    const startMin = Math.max(0, (start - dayStart) / 60000);
    let endMin = Math.min(1440, (end - dayStart) / 60000);
    if (endMin - startMin < 30) endMin = startMin + 30; // keep it visible
    raw.push({ event, startMin, endMin });
  }

  return { allDay, timed: packEventColumns(raw) };
}

/**
 * Greedy column packing for overlapping timed segments: each segment gets a
 * `col` index and the `cols` count of its overlap cluster, so the UI can place
 * concurrent events side by side (`width = 100/cols%`, `left = col*width`).
 */
export function packEventColumns(segments) {
  const segs = [...segments].sort(
    (a, b) => a.startMin - b.startMin || a.endMin - b.endMin,
  );
  const result = [];
  let cluster = [];
  let clusterEnd = -1;

  const flush = () => {
    const colEnds = [];
    for (const seg of cluster) {
      let col = colEnds.findIndex((end) => seg.startMin >= end);
      if (col === -1) {
        col = colEnds.length;
        colEnds.push(seg.endMin);
      } else {
        colEnds[col] = seg.endMin;
      }
      seg.col = col;
    }
    for (const seg of cluster) result.push({ ...seg, cols: colEnds.length });
    cluster = [];
    clusterEnd = -1;
  };

  for (const seg of segs) {
    if (cluster.length && seg.startMin >= clusterEnd) flush();
    cluster.push(seg);
    clusterEnd = Math.max(clusterEnd, seg.endMin);
  }
  flush();
  return result;
}

/**
 * Build the 6x7 matrix (42 days) covering the month of `date`, starting on
 * Monday. Returns a flat array of Date objects.
 */
export function buildMonthMatrix(date) {
  const first = startOfMonth(date);
  const offset = (first.getDay() + 6) % 7; // Monday = 0
  const start = new Date(first);
  start.setDate(first.getDate() - offset);

  const days = [];
  for (let i = 0; i < 42; i += 1) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    days.push(day);
  }
  return days;
}

/** Local `YYYY-MM-DD` key, handy for grouping items by day. */
export function dayKey(value) {
  const d = new Date(value);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** True if both values fall on the same calendar day (local time). */
export function isSameDay(a, b) {
  return dayKey(a) === dayKey(b);
}

/**
 * Maps each event onto every grid day it covers, from its start day to its end
 * day (inclusive). Events without an `end` cover only their start day. Returns
 * `{ dayKey: [{ event, isStart, isEnd }] }` so a multi-day event shows on each
 * day it spans instead of only on its start day.
 */
export function eventSegmentsByDay(events, days) {
  const map = {};
  for (const event of events) {
    const a = dayKey(event.start);
    const b = event.end ? dayKey(event.end) : a;
    const [from, to] = a <= b ? [a, b] : [b, a];
    for (const day of days) {
      const key = dayKey(day);
      if (key >= from && key <= to) {
        (map[key] ||= []).push({
          event,
          isStart: key === from,
          isEnd: key === to,
        });
      }
    }
  }
  return map;
}

/** True if `value` is within the month of `monthDate`. */
export function isSameMonth(value, monthDate) {
  const d = new Date(value);
  return (
    d.getFullYear() === monthDate.getFullYear() &&
    d.getMonth() === monthDate.getMonth()
  );
}

/** Human month label, e.g. "July 2026". */
export function monthLabel(date) {
  return date.toLocaleDateString([], { month: "long", year: "numeric" });
}

/** Convert a date/ISO value to a `datetime-local` input string (local time). */
export function toDateTimeLocal(value) {
  const d = new Date(value);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Convert a `datetime-local` string (local time) to an ISO 8601 UTC string. */
export function fromDateTimeLocal(value) {
  return new Date(value).toISOString();
}
