<template>
  <div>
    <div class="overflow-x-auto pb-1">
      <div class="inline-flex flex-col gap-1">
        <!-- Month labels -->
        <div class="flex gap-1 pl-8">
          <div
            v-for="(col, w) in grid.columns"
            :key="`m-${w}`"
            class="w-3 text-[10px] text-muted-foreground">
            {{ monthLabelByWeek[w] || "" }}
          </div>
        </div>

        <div class="flex gap-1">
          <!-- Weekday labels -->
          <div class="flex w-7 flex-col gap-1 pr-1 text-[9px] text-muted-foreground">
            <span
              v-for="(label, d) in WEEKDAYS"
              :key="`wd-${d}`"
              class="flex h-3 items-center">
              {{ label }}
            </span>
          </div>

          <!-- Week columns -->
          <div
            v-for="(col, w) in grid.columns"
            :key="`c-${w}`"
            class="flex flex-col gap-1">
            <div
              v-for="cell in col"
              :key="cell.date"
              class="size-3 rounded-sm"
              :class="cell.future ? 'opacity-0' : LEVELS[cell.level]"
              :title="
                cell.future ? '' : `${cell.date}: ${formatHours(cell.hours)}`
              "></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div
      class="mt-3 flex items-center justify-end gap-1.5 text-[11px] text-muted-foreground">
      <span>Less</span>
      <span
        v-for="(cls, level) in LEVELS"
        :key="`lg-${level}`"
        class="size-3 rounded-sm"
        :class="cls"></span>
      <span>More</span>
    </div>
  </div>
</template>

<script setup>
  import { computed } from "vue";

  const props = defineProps({
    buckets: { type: Array, default: () => [] },
    weeks: { type: Number, default: 53 },
  });

  // Monday-started, matching the backend's week bucketing; only alternate rows
  // are labelled to keep the axis uncluttered.
  const WEEKDAYS = ["Mon", "", "Wed", "", "Fri", "", ""];

  const LEVELS = [
    "bg-border/60",
    "bg-primary/25",
    "bg-primary/45",
    "bg-primary/70",
    "bg-primary",
  ];

  const grid = computed(() =>
    heatmapGrid(props.buckets, { weeks: props.weeks }),
  );

  const monthLabelByWeek = computed(() => {
    const map = {};
    for (const label of grid.value.monthLabels) map[label.week] = label.text;
    return map;
  });
</script>
