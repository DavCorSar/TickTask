<template>
  <div>
    <div class="flex items-center justify-center">
      <div class="relative">
        <svg
          :viewBox="`0 0 ${SIZE} ${SIZE}`"
          class="h-40 w-40"
          role="img"
          aria-label="Share of tracked time by task">
          <!-- Track -->
          <circle
            :cx="C"
            :cy="C"
            :r="R"
            fill="none"
            class="stroke-border"
            :stroke-width="THICKNESS" />
          <!-- One arc per task -->
          <circle
            v-for="seg in donut.segments"
            :key="seg.taskId"
            :cx="C"
            :cy="C"
            :r="R"
            fill="none"
            :stroke="seg.color"
            :stroke-width="THICKNESS"
            :stroke-dasharray="`${seg.fraction * CIRC} ${CIRC}`"
            :transform="`rotate(${-90 + seg.offset * 360} ${C} ${C})`">
            <title>{{ seg.name }} · {{ formatHours(seg.hours) }} ({{ seg.percent }}%)</title>
          </circle>
        </svg>
        <div
          class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span class="text-lg font-bold tracking-tight">{{
            formatHours(donut.total)
          }}</span>
          <span class="text-[11px] text-muted-foreground">tracked</span>
        </div>
      </div>
    </div>

    <div v-if="donut.segments.length" class="mt-4 space-y-1.5">
      <div
        v-for="seg in donut.segments"
        :key="seg.taskId"
        class="flex items-center gap-2 text-sm">
        <span
          class="size-2.5 shrink-0 rounded-full"
          :style="{ backgroundColor: seg.color }"></span>
        <span
          class="truncate"
          :class="seg.deleted ? 'text-muted-foreground line-through' : ''"
          >{{ seg.name }}</span
        >
        <span class="ml-auto shrink-0 tabular-nums text-muted-foreground">
          {{ seg.percent }}% · {{ formatHours(seg.hours) }}
        </span>
      </div>
    </div>
    <p v-else class="mt-4 text-center text-sm text-muted-foreground">
      No tracked time in this range.
    </p>
  </div>
</template>

<script setup>
  import { computed } from "vue";

  const props = defineProps({
    tasks: { type: Array, default: () => [] },
  });

  const SIZE = 120;
  const C = SIZE / 2;
  const THICKNESS = 18;
  const R = C - THICKNESS / 2;
  const CIRC = 2 * Math.PI * R;

  const donut = computed(() => donutSegments(props.tasks));
</script>
