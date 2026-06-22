<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Dashboard</h1>
      <p class="mt-1 text-muted-foreground">
        Hours spent across your tasks and subtasks.
      </p>
    </div>

    <UiAlert v-if="error" variant="danger">
      Couldn't load your dashboard. Please try again.
    </UiAlert>

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
          <DashboardTaskBreakdown :tasks="series?.by_task || []" />
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

  const { $api } = useNuxtApp();

  const bucket = ref("day");
  const summary = ref(null);
  const series = ref(null);
  const seriesLoading = ref(false);
  const error = ref(false);

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
      summary.value = await $api("/dashboard/user/get-summary/", {
        method: "GET",
      });
    } catch (err) {
      console.error("Error loading dashboard summary:", err);
      error.value = true;
    }
  }

  async function loadSeries() {
    seriesLoading.value = true;
    try {
      const { start, end } = rangeForBucket(bucket.value);
      series.value = await $api("/dashboard/user/get-time-series/", {
        method: "GET",
        query: {
          start: start.toISOString(),
          end: end.toISOString(),
          bucket: bucket.value,
        },
      });
    } catch (err) {
      console.error("Error loading dashboard series:", err);
      error.value = true;
    } finally {
      seriesLoading.value = false;
    }
  }

  onMounted(loadSummary);
  watch(bucket, loadSeries, { immediate: true });
</script>
