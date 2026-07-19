// Pure helpers for the notes view. Kept framework-free so they are easy to unit
// test. Auto-imported across the app by Nuxt (utils/).

/** Accent colors offered when creating or editing a note group. */
export const NOTE_COLORS = [
  "#007CBF",
  "#5EA611",
  "#D30F4B",
  "#F59E0B",
  "#7C3AED",
  "#0EA5E9",
];

/**
 * Orders a group's notes for display: pending items first (by their manual
 * `order`, then creation time), with done items sinking to the bottom. Returns
 * a new array and never mutates the input.
 */
export function sortNotes(notes = []) {
  return [...notes].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1;
    if (a.order !== b.order) return a.order - b.order;
    return new Date(a.created_at) - new Date(b.created_at);
  });
}

/**
 * Progress of a group as `{ done, total, percent }`, where `percent` is the
 * share of its notes that are done (0 when the group is empty).
 */
export function groupProgress(notes = []) {
  const total = notes.length;
  const done = notes.filter((note) => note.done).length;
  const percent = total ? Math.round((done / total) * 100) : 0;
  return { done, total, percent };
}
