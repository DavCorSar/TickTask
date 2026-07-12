<template>
  <div>
    <div class="relative">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        class="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        :aria-label="`Tracked hours per ${bucket}, stacked by task`">
        <!-- Gridlines + y-axis labels -->
        <g>
          <line
            v-for="tick in geometry.yTicks"
            :key="`grid-${tick.value}`"
            :x1="PAD.left"
            :x2="W - PAD.right"
            :y1="tick.y"
            :y2="tick.y"
            class="stroke-border"
            stroke-width="1" />
          <text
            v-for="tick in geometry.yTicks"
            :key="`ylabel-${tick.value}`"
            :x="PAD.left - 8"
            :y="tick.y + 3"
            text-anchor="end"
            class="fill-muted-foreground text-[10px]">
            {{ tick.value }}
          </text>
        </g>

        <!-- Stacked bars -->
        <g v-for="bar in geometry.bars" :key="`bar-${bar.i}`">
          <rect
            v-for="seg in bar.rects"
            :key="`${bar.i}-${seg.taskId}`"
            :x="bar.x"
            :y="seg.y"
            :width="bar.width"
            :height="seg.height"
            :fill="seg.color">
            <title>{{ seg.name }} · {{ formatHours(seg.hours) }}</title>
          </rect>
        </g>

        <!-- X-axis labels -->
        <text
          v-for="label in geometry.xLabels"
          :key="`xlabel-${label.period_start}`"
          :x="label.x"
          :y="H - 8"
          text-anchor="middle"
          class="fill-muted-foreground text-[10px]">
          {{ label.text }}
        </text>
      </svg>

      <div
        v-if="geometry.message"
        class="pointer-events-none absolute inset-0 flex items-center justify-center">
        <p class="text-sm text-muted-foreground">{{ geometry.message }}</p>
      </div>
    </div>

    <!-- Legend -->
    <div v-if="legend.length" class="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
      <span
        v-for="entry in legend"
        :key="entry.taskId"
        class="flex items-center gap-1.5 text-xs font-medium"
        :class="entry.deleted ? 'text-muted-foreground' : 'text-foreground'">
        <span
          class="size-2.5 rounded-full"
          :style="{ backgroundColor: entry.color }"></span>
        <span :class="{ 'line-through': entry.deleted }">{{ entry.name }}</span>
      </span>
    </div>
  </div>
</template>

<script setup>
  import { computed } from "vue";

  const props = defineProps({
    buckets: { type: Array, default: () => [] },
    tasks: { type: Array, default: () => [] },
    bucket: { type: String, default: "day" },
  });

  const W = 720;
  const H = 240;
  const PAD = { top: 16, right: 16, bottom: 28, left: 36 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const TICKS = 4;

  // Only tasks with tracked time in the range make it into the legend/stacks.
  const legend = computed(() => {
    const withTime = new Set();
    props.tasks.forEach((task) => {
      if ((task.series || []).some((h) => h > 0)) withTime.add(task.task_id);
    });
    return props.tasks
      .map((task, index) => ({
        taskId: task.task_id,
        name: task.task_name,
        deleted: task.deleted,
        color: chartColor(index),
      }))
      .filter((entry) => withTime.has(entry.taskId));
  });

  const geometry = computed(() => {
    const stacks = stackedBuckets(props.buckets, props.tasks);
    const n = stacks.length;
    const niceMax = niceCeil(Math.max(0, ...stacks.map((s) => s.total)));

    const band = n ? innerW / n : innerW;
    const barWidth = Math.max(band * 0.7, 1);
    const xAt = (i) => PAD.left + i * band + (band - barWidth) / 2;
    const yAt = (h) => PAD.top + innerH - (h / niceMax) * innerH;

    const bars = stacks.map((stack, i) => {
      let acc = 0;
      const rects = stack.segments.map((seg) => {
        const y = yAt(acc + seg.hours);
        const height = (seg.hours / niceMax) * innerH;
        acc += seg.hours;
        return { ...seg, y, height };
      });
      return { i, x: xAt(i), width: barWidth, rects };
    });

    const yTicks = Array.from({ length: TICKS + 1 }, (_, k) => {
      const value = (niceMax / TICKS) * k;
      return { value: Math.round(value * 10) / 10, y: yAt(value) };
    });

    const labelEvery = Math.max(1, Math.ceil(n / 6));
    const xLabels = stacks
      .map((stack, i) => ({
        x: xAt(i) + barWidth / 2,
        period_start: stack.period_start,
        text: formatBucketLabel(stack.period_start, props.bucket),
      }))
      .filter((_, i) => i % labelEvery === 0 || i === n - 1);

    const message = stacks.some((s) => s.total > 0)
      ? ""
      : "No tracked time in this range.";

    return { bars, yTicks, xLabels, message };
  });
</script>
