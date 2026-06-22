<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">History</h1>
        <p class="mt-1 text-muted-foreground">
          Browse and review your past time entries.
        </p>
      </div>
      <label
        class="flex cursor-pointer select-none items-center gap-2 text-sm text-muted-foreground">
        <input
          v-model="includeDeleted"
          type="checkbox"
          class="size-4 rounded border-border accent-primary" />
        Show deleted
      </label>
    </div>

    <!-- Controls -->
    <UiCard>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="inline-flex rounded-xl border border-border p-0.5">
          <button
            v-for="option in RANGES"
            :key="option.value"
            class="rounded-lg px-3 py-1 text-sm font-medium transition-colors"
            :class="
              range === option.value
                ? 'bg-primary text-primary-foreground shadow-soft'
                : 'text-muted-foreground hover:text-foreground'
            "
            @click="range = option.value">
            {{ option.label }}
          </button>
        </div>
        <div class="sm:w-64">
          <UiInput
            v-model="search"
            icon="lucide:search"
            placeholder="Search by task or subtask" />
        </div>
      </div>
      <p class="mt-3 text-sm text-muted-foreground">
        {{ totalEntries }} {{ totalEntries === 1 ? "entry" : "entries" }} ·
        {{ formatDuration(totalMs) }} tracked
      </p>
    </UiCard>

    <!-- Loading -->
    <UiCard v-if="loading">
      <div class="flex items-center justify-center py-12 text-muted-foreground">
        <Icon name="lucide:loader-circle" class="size-6 animate-spin" />
      </div>
    </UiCard>

    <!-- Empty -->
    <UiCard v-else-if="!groups.length">
      <div class="flex flex-col items-center gap-3 py-12 text-center">
        <div
          class="flex size-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <Icon name="lucide:history" class="size-6" />
        </div>
        <div>
          <p class="font-medium">No time entries</p>
          <p class="text-sm text-muted-foreground">
            {{
              search
                ? "Nothing matches your search in this range."
                : "Nothing tracked in this range yet."
            }}
          </p>
        </div>
      </div>
    </UiCard>

    <!-- Grouped by day -->
    <div v-else class="space-y-5">
      <div v-for="group in groups" :key="group.key">
        <div class="mb-2 flex items-baseline justify-between px-1">
          <h2 class="text-sm font-semibold">{{ formatDay(group.date) }}</h2>
          <span class="text-xs font-medium tabular-nums text-muted-foreground">
            {{ formatDuration(group.totalMs) }}
          </span>
        </div>
        <UiCard :padded="false">
          <ul class="divide-y divide-border">
            <li
              v-for="entry in group.entries"
              :key="entry.id"
              class="flex items-center gap-3 px-4 py-3">
              <span class="w-24 shrink-0 text-sm tabular-nums text-muted-foreground">
                {{ formatClock(entry.clock_in) }} –
                {{ entry.clock_out ? formatClock(entry.clock_out) : "now" }}
              </span>
              <span class="min-w-0 flex-1 truncate text-sm">
                <span
                  class="font-medium"
                  :class="{ 'text-muted-foreground line-through': entry.deleted }">
                  {{ entry.task_name }}
                </span>
                <span class="text-muted-foreground">› {{ entry.subtask_name }}</span>
                <span
                  v-if="entry.deleted"
                  class="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  deleted
                </span>
              </span>
              <span
                class="shrink-0 text-sm font-semibold tabular-nums"
                :class="{ 'text-muted-foreground': !entry.clock_out }">
                {{ formatDuration(durationMs(entry)) }}
              </span>
            </li>
          </ul>
        </UiCard>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { ref, computed, watch } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { getTimeHistory } = useTasks();
  const toast = useToast();

  const RANGES = [
    { value: "7", label: "7 days", days: 7 },
    { value: "30", label: "30 days", days: 30 },
    { value: "90", label: "90 days", days: 90 },
    { value: "all", label: "All", days: null },
  ];

  const range = ref("30");
  const search = ref("");
  const includeDeleted = ref(false);
  const entries = ref([]);
  const loading = ref(false);

  function durationMs(entry) {
    const end = entry.clock_out ? new Date(entry.clock_out) : new Date();
    return Math.max(0, end - new Date(entry.clock_in));
  }

  function formatDay(date) {
    return date.toLocaleDateString([], {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  const filtered = computed(() => {
    const query = search.value.trim().toLowerCase();
    if (!query) return entries.value;
    return entries.value.filter(
      (entry) =>
        entry.task_name.toLowerCase().includes(query) ||
        entry.subtask_name.toLowerCase().includes(query),
    );
  });

  const groups = computed(() => {
    // Entries arrive newest-first, so days are first seen in descending order.
    const map = new Map();
    for (const entry of filtered.value) {
      const key = dayKey(new Date(entry.clock_in));
      if (!map.has(key)) {
        map.set(key, {
          key,
          date: new Date(entry.clock_in),
          entries: [],
          totalMs: 0,
        });
      }
      const group = map.get(key);
      group.entries.push(entry);
      group.totalMs += durationMs(entry);
    }
    return Array.from(map.values());
  });

  const totalEntries = computed(() => filtered.value.length);
  const totalMs = computed(() =>
    filtered.value.reduce((sum, entry) => sum + durationMs(entry), 0),
  );

  async function load() {
    loading.value = true;
    try {
      const option = RANGES.find((r) => r.value === range.value);
      const end = new Date();
      let start;
      if (option.days === null) {
        // "All" — reach back far enough to cover every entry.
        start = new Date(0);
      } else {
        start = new Date(end);
        start.setDate(start.getDate() - option.days);
        start.setHours(0, 0, 0, 0);
      }
      entries.value = await getTimeHistory(
        start.toISOString(),
        end.toISOString(),
        includeDeleted.value,
      );
    } catch (err) {
      console.error("Error loading history:", err);
      toast.error("Couldn't load your history.");
    } finally {
      loading.value = false;
    }
  }

  watch([range, includeDeleted], load, { immediate: true });
</script>
