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
