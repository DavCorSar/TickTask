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
        </template>

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
  </div>
</template>

<script setup>
  import { ref, computed, watch, onMounted } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { getSummary, getTimeSeries } = useDashboard();
  const { restoreTask: apiRestoreTask, restoreSubtask: apiRestoreSubtask } =
    useTasks();
  const toast = useToast();

  const bucket = ref("day");
  const includeDeleted = ref(false);
  const summary = ref(null);
  const series = ref(null);
  const seriesLoading = ref(false);

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

  async function loadSeries() {
    seriesLoading.value = true;
    try {
      const { start, end } = rangeForBucket(bucket.value);
      series.value = await getTimeSeries(
        start.toISOString(),
        end.toISOString(),
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

  async function restoreTask(taskId) {
    try {
      await apiRestoreTask(taskId);
      toast.success("Task restored.");
      await Promise.all([loadSummary(), loadSeries()]);
    } catch (err) {
      console.error("Error restoring task:", err);
      toast.error("Couldn't restore the task.");
    }
  }

  async function restoreSubtask(subtaskId) {
    try {
      await apiRestoreSubtask(subtaskId);
      toast.success("Subtask restored.");
      await Promise.all([loadSummary(), loadSeries()]);
    } catch (err) {
      console.error("Error restoring subtask:", err);
      toast.error("Couldn't restore the subtask.");
    }
  }

  onMounted(loadSummary);
  watch(bucket, loadSeries, { immediate: true });
  watch(includeDeleted, () => Promise.all([loadSummary(), loadSeries()]));
</script>
