<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Dashboard</h1>
        <p class="mt-1 text-muted-foreground">
          Hours spent across your tasks and subtasks.
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

    <!-- Stat cards -->
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <DashboardStatCard
        v-for="card in statCards"
        :key="card.label"
        :label="card.label"
        :value="card.value"
        :hint="card.hint"
        :icon="card.icon" />
    </div>

    <!-- Charts -->
    <div class="grid gap-6 lg:grid-cols-3">
      <UiCard class="lg:col-span-2">
        <template #header>
          <h3 class="text-base font-semibold tracking-tight">
            Tracked hours by task
          </h3>
          <p class="mt-0.5 text-sm text-muted-foreground">{{ rangeLabel }}</p>
        </template>
        <template #actions>
          <div class="flex flex-wrap items-center justify-end gap-2">
            <div class="inline-flex rounded-xl border border-border p-0.5">
              <button
                v-for="option in RANGE_OPTIONS"
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
              <button
                class="rounded-lg px-3 py-1 text-sm font-medium transition-colors"
                :class="
                  range === 'custom'
                    ? 'bg-primary text-primary-foreground shadow-soft'
                    : 'text-muted-foreground hover:text-foreground'
                "
                @click="selectCustomRange">
                Custom
              </button>
            </div>
            <div class="inline-flex rounded-xl border border-border p-0.5">
              <button
                v-for="option in BUCKET_OPTIONS"
                :key="option.value"
                class="rounded-lg px-3 py-1 text-sm font-medium transition-colors"
                :class="
                  bucket === option.value
                    ? 'bg-primary text-primary-foreground shadow-soft'
                    : 'text-muted-foreground hover:text-foreground'
                "
                @click="bucket = option.value">
                {{ option.label }}
              </button>
            </div>
          </div>
        </template>

        <div
          v-if="range === 'custom'"
          class="mb-4 flex flex-wrap items-center gap-2 text-sm">
          <label class="flex items-center gap-1.5 text-muted-foreground">
            From
            <input
              v-model="customStart"
              type="date"
              :max="customEnd || undefined"
              class="rounded-lg border border-border bg-background px-2 py-1 text-foreground" />
          </label>
          <label class="flex items-center gap-1.5 text-muted-foreground">
            To
            <input
              v-model="customEnd"
              type="date"
              :min="customStart || undefined"
              class="rounded-lg border border-border bg-background px-2 py-1 text-foreground" />
          </label>
        </div>

        <div class="relative min-h-[240px]">
          <div
            v-if="seriesLoading"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
            <Icon
              name="lucide:loader-circle"
              class="size-6 animate-spin text-muted-foreground" />
          </div>
          <DashboardTrendChart
            :buckets="series?.buckets || []"
            :tasks="series?.by_task || []"
            :bucket="bucket" />
        </div>
      </UiCard>

      <UiCard title="Hours per task" subtitle="In the selected range">
        <div class="relative min-h-[240px]">
          <div
            v-if="seriesLoading"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
            <Icon
              name="lucide:loader-circle"
              class="size-6 animate-spin text-muted-foreground" />
          </div>
          <DashboardTaskBreakdown
            :tasks="series?.by_task || []"
            @restore-task="restoreTask"
            @restore-subtask="restoreSubtask" />
        </div>
      </UiCard>
    </div>

    <!-- Composition + share -->
    <div class="grid gap-6 lg:grid-cols-3">
      <UiCard
        class="lg:col-span-2"
        title="Composition over time"
        :subtitle="rangeLabel">
        <div class="relative min-h-[240px]">
          <div
            v-if="seriesLoading"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
            <Icon
              name="lucide:loader-circle"
              class="size-6 animate-spin text-muted-foreground" />
          </div>
          <DashboardStackedBar
            :buckets="series?.buckets || []"
            :tasks="series?.by_task || []"
            :bucket="bucket" />
        </div>
      </UiCard>

      <UiCard title="Share by task" subtitle="In the selected range">
        <div class="relative min-h-[240px]">
          <div
            v-if="seriesLoading"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
            <Icon
              name="lucide:loader-circle"
              class="size-6 animate-spin text-muted-foreground" />
          </div>
          <DashboardDonut :tasks="series?.by_task || []" />
        </div>
      </UiCard>
    </div>

    <!-- Daily activity heatmap -->
    <UiCard title="Daily activity" subtitle="Hours tracked per day over the last year">
      <div class="relative min-h-[160px]">
        <div
          v-if="heatmapLoading"
          class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
          <Icon
            name="lucide:loader-circle"
            class="size-6 animate-spin text-muted-foreground" />
        </div>
        <DashboardHeatmap :buckets="heatmap?.buckets || []" />
      </div>
    </UiCard>

    <!-- Share of the last 7 days, per task -->
    <UiCard title="This week by task" subtitle="Share of time tracked in the last 7 days">
      <div class="relative min-h-[200px]">
        <div
          v-if="weeklyLoading"
          class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
          <Icon
            name="lucide:loader-circle"
            class="size-6 animate-spin text-muted-foreground" />
        </div>
        <DashboardWeeklyShare :tasks="weekly?.tasks || []" />
      </div>
    </UiCard>
  </div>
</template>

<script setup>
  import { ref, computed, watch, onMounted } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { getSummary, getTimeSeries, getWeeklyTaskHours } = useDashboard();
  const { restoreTask: apiRestoreTask, restoreSubtask: apiRestoreSubtask } =
    useTasks();
  const toast = useToast();

  const bucket = ref("day");
  const range = ref(30);
  const customStart = ref("");
  const customEnd = ref("");
  const includeDeleted = ref(false);
  const summary = ref(null);
  const series = ref(null);
  const seriesLoading = ref(false);
  const weekly = ref(null);
  const weeklyLoading = ref(false);
  const heatmap = ref(null);
  const heatmapLoading = ref(false);

  // The heatmap always shows a fixed trailing year of daily data, independent
  // of the trend chart's range/bucket selection.
  const HEATMAP_DAYS = 53 * 7;

  const statCards = computed(() => {
    const s = summary.value;
    return [
      {
        label: "Today",
        value: s ? formatHours(s.today_hours) : "—",
        icon: "lucide:clock",
      },
      {
        label: "This week",
        value: s ? formatHours(s.week_hours) : "—",
        icon: "lucide:calendar-days",
      },
      {
        label: "Total tracked",
        value: s ? formatHours(s.total_hours) : "—",
        icon: "lucide:hourglass",
      },
      {
        label: "Active tasks",
        value: s ? s.active_tasks : "—",
        hint: "worked on this week",
        icon: "lucide:list-checks",
      },
    ];
  });

  const rangeLabel = computed(() => {
    if (!series.value) return "";
    const fmt = (d) =>
      new Date(d).toLocaleDateString([], {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    return `${fmt(series.value.start)} – ${fmt(series.value.end)}`;
  });

  async function loadSummary() {
    try {
      summary.value = await getSummary(includeDeleted.value);
    } catch (err) {
      console.error("Error loading dashboard summary:", err);
      toast.error("Couldn't load the dashboard summary.");
    }
  }

  async function loadWeekly() {
    weeklyLoading.value = true;
    try {
      weekly.value = await getWeeklyTaskHours(includeDeleted.value);
    } catch (err) {
      console.error("Error loading weekly task hours:", err);
      toast.error("Couldn't load this week's breakdown.");
    } finally {
      weeklyLoading.value = false;
    }
  }

  // Resolves the current selection to a `{ start, end }` range, or null when a
  // custom range is incomplete/invalid (nothing to load yet).
  function currentRange() {
    if (range.value !== "custom") return rangeForDays(range.value);
    if (!customStart.value || !customEnd.value) return null;
    const start = new Date(`${customStart.value}T00:00:00`);
    const end = new Date(`${customEnd.value}T23:59:59.999`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
    if (end < start) return null;
    return { start, end };
  }

  // Switches to a custom range, seeding the inputs from the last 30 days so
  // they are never empty when the pickers first appear.
  function selectCustomRange() {
    if (!customStart.value || !customEnd.value) {
      const { start, end } = rangeForDays(30);
      customStart.value = toDateInput(start);
      customEnd.value = toDateInput(end);
    }
    range.value = "custom";
  }

  async function loadSeries() {
    const window = currentRange();
    if (!window) return;
    seriesLoading.value = true;
    try {
      series.value = await getTimeSeries(
        window.start.toISOString(),
        window.end.toISOString(),
        bucket.value,
        includeDeleted.value,
      );
    } catch (err) {
      console.error("Error loading dashboard series:", err);
      toast.error("Couldn't load the dashboard chart.");
    } finally {
      seriesLoading.value = false;
    }
  }

  async function loadHeatmap() {
    heatmapLoading.value = true;
    try {
      const { start, end } = rangeForDays(HEATMAP_DAYS);
      heatmap.value = await getTimeSeries(
        start.toISOString(),
        end.toISOString(),
        "day",
        includeDeleted.value,
      );
    } catch (err) {
      console.error("Error loading dashboard heatmap:", err);
      toast.error("Couldn't load the activity heatmap.");
    } finally {
      heatmapLoading.value = false;
    }
  }

  async function restoreTask(taskId) {
    try {
      await apiRestoreTask(taskId);
      toast.success("Task restored.");
      await Promise.all([loadSummary(), loadSeries(), loadWeekly(), loadHeatmap()]);
    } catch (err) {
      console.error("Error restoring task:", err);
      toast.error("Couldn't restore the task.");
    }
  }

  async function restoreSubtask(subtaskId) {
    try {
      await apiRestoreSubtask(subtaskId);
      toast.success("Subtask restored.");
      await Promise.all([loadSummary(), loadSeries(), loadWeekly(), loadHeatmap()]);
    } catch (err) {
      console.error("Error restoring subtask:", err);
      toast.error("Couldn't restore the subtask.");
    }
  }

  onMounted(() => Promise.all([loadSummary(), loadWeekly(), loadHeatmap()]));
  watch([bucket, range, customStart, customEnd], loadSeries, { immediate: true });
  watch(includeDeleted, () =>
    Promise.all([loadSummary(), loadSeries(), loadWeekly(), loadHeatmap()]),
  );
</script>
