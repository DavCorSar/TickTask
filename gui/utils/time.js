// Pure time-formatting helpers, kept framework-free so they're easy to unit test.
// Auto-imported across the app by Nuxt (utils/ directory).

/**
 * Format a duration given in milliseconds as `HH:MM:SS`.
 * Negative values are clamped to zero.
 */
export function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

/**
 * Format a date/timestamp as a short local clock time (e.g. `14:05`).
 */
export function formatClock(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}
