import { describe, it, expect } from "vitest";
import { sortNotes, groupProgress, NOTE_COLORS } from "../utils/notes.js";

describe("sortNotes", () => {
  it("keeps pending notes before done ones", () => {
    const notes = [
      { id: 1, done: true, order: 1, created_at: "2026-01-01" },
      { id: 2, done: false, order: 2, created_at: "2026-01-01" },
    ];
    expect(sortNotes(notes).map((n) => n.id)).toEqual([2, 1]);
  });

  it("orders by manual order, then creation time, within a done state", () => {
    const notes = [
      { id: 1, done: false, order: 2, created_at: "2026-01-02" },
      { id: 2, done: false, order: 1, created_at: "2026-01-05" },
      { id: 3, done: false, order: 2, created_at: "2026-01-01" },
    ];
    expect(sortNotes(notes).map((n) => n.id)).toEqual([2, 3, 1]);
  });

  it("does not mutate the input array", () => {
    const notes = [
      { id: 1, done: true, order: 1, created_at: "2026-01-01" },
      { id: 2, done: false, order: 2, created_at: "2026-01-01" },
    ];
    const copy = [...notes];
    sortNotes(notes);
    expect(notes).toEqual(copy);
  });

  it("handles an empty / missing list", () => {
    expect(sortNotes()).toEqual([]);
    expect(sortNotes([])).toEqual([]);
  });
});

describe("groupProgress", () => {
  it("counts done vs total and the percent", () => {
    const notes = [{ done: true }, { done: false }, { done: true }, { done: false }];
    expect(groupProgress(notes)).toEqual({ done: 2, total: 4, percent: 50 });
  });

  it("reports 0% for an empty group without dividing by zero", () => {
    expect(groupProgress([])).toEqual({ done: 0, total: 0, percent: 0 });
    expect(groupProgress()).toEqual({ done: 0, total: 0, percent: 0 });
  });

  it("rounds the percent", () => {
    const notes = [{ done: true }, { done: false }, { done: false }];
    expect(groupProgress(notes).percent).toBe(33);
  });
});

describe("NOTE_COLORS", () => {
  it("is a non-empty list of hex colors", () => {
    expect(NOTE_COLORS.length).toBeGreaterThan(0);
    for (const c of NOTE_COLORS) expect(c).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });
});
