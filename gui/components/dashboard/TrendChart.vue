<template>
  <div>
    <div class="relative">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        class="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        :aria-label="`Tracked hours per ${bucket} and task`">
        <!-- Horizontal gridlines + y-axis labels -->
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

        <!-- One line per visible task -->
        <g v-for="line in geometry.lines" :key="`line-${line.taskId}`">
          <path
            :d="line.path"
            fill="none"
            :stroke="line.color"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round" />
          <circle
            v-for="point in line.dots"
            :key="`${line.taskId}-${point.i}`"
            :cx="point.x"
            :cy="point.y"
            r="2.5"
            :fill="line.color"
            stroke-width="1.5"
            class="stroke-card">
            <title>{{ line.name }} · {{ point.tooltip }}</title>
          </circle>
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

    <!-- Legend: click to show/hide a task's line -->
    <div v-if="tasks.length" class="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
      <button
        v-for="entry in legend"
        :key="entry.taskId"
        class="flex items-center gap-1.5 text-xs font-medium transition-colors"
        :class="entry.hidden ? 'text-muted-foreground/60' : 'text-foreground'"
        :title="entry.hidden ? 'Show this task' : 'Hide this task'"
        @click="toggle(entry.taskId)">
        <span
          class="size-2.5 rounded-full transition-opacity"
          :style="{
            backgroundColor: entry.color,
            opacity: entry.hidden ? 0.3 : 1,
          }"></span>
        <span :class="{ 'line-through': entry.hidden || entry.deleted }">{{
          entry.name
        }}</span>
        <span
          v-if="entry.deleted"
          class="text-[10px] uppercase tracking-wide text-muted-foreground"
          >(deleted)</span
        >
        <span class="text-muted-foreground">{{
          formatHours(entry.hours)
        }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
  import { computed, reactive } from "vue";

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

  const hidden = reactive(new Set());

  function toggle(taskId) {
    if (hidden.has(taskId)) hidden.delete(taskId);
    else hidden.add(taskId);
  }

  const legend = computed(() =>
    props.tasks.map((task, index) => ({
      taskId: task.task_id,
      name: task.task_name,
      hours: task.hours,
      deleted: task.deleted,
      color: chartColor(index),
      hidden: hidden.has(task.task_id),
    })),
  );

  const geometry = computed(() => {
    const n = props.buckets.length;
    const visible = props.tasks
      .map((task, index) => ({ task, color: chartColor(index) }))
      .filter(({ task }) => !hidden.has(task.task_id));

    const maxValue = Math.max(
      0,
      ...visible.flatMap(({ task }) => task.series || []),
    );
    const niceMax = niceCeil(maxValue);

    const xAt = (i) =>
      n <= 1 ? PAD.left + innerW / 2 : PAD.left + (i / (n - 1)) * innerW;
    const yAt = (h) => PAD.top + innerH - (h / niceMax) * innerH;

    const lines = visible.map(({ task, color }) => {
      const points = (task.series || []).map((hours, i) => ({
        i,
        x: xAt(i),
        y: yAt(hours),
        hours,
        tooltip: `${labelAt(i)}: ${formatHours(hours)}`,
      }));
      return {
        taskId: task.task_id,
        name: task.task_name,
        color,
        path: points
          .map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
          .join(" "),
        dots: points.filter((p) => p.hours > 0),
      };
    });

    const yTicks = Array.from({ length: TICKS + 1 }, (_, k) => {
      const value = (niceMax / TICKS) * k;
      return { value: Math.round(value * 10) / 10, y: yAt(value) };
    });

    const labelEvery = Math.max(1, Math.ceil(n / 6));
    const xLabels = props.buckets
      .map((b, i) => ({
        x: xAt(i),
        period_start: b.period_start,
        text: labelAt(i),
      }))
      .filter((_, i) => i % labelEvery === 0 || i === n - 1);

    let message = "";
    if (!props.tasks.length) message = "No tracked time in this range.";
    else if (!visible.length) message = "All tasks hidden.";

    return { lines, yTicks, xLabels, message };
  });

  function labelAt(i) {
    const b = props.buckets[i];
    return b ? formatBucketLabel(b.period_start, props.bucket) : "";
  }
</script>
