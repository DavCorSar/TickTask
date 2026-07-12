<template>
  <div>
    <div class="relative" @mouseleave="activeIndex = null">
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

        <!-- Vertical crosshair at the hovered bucket -->
        <line
          v-if="activeIndex !== null"
          :x1="geometry.xByIndex[activeIndex]"
          :x2="geometry.xByIndex[activeIndex]"
          :y1="PAD.top"
          :y2="PAD.top + innerH"
          class="stroke-muted-foreground/40"
          stroke-width="1"
          stroke-dasharray="3 3" />

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
            :r="activeIndex === point.i ? 4 : 2.5"
            :fill="line.color"
            stroke-width="1.5"
            class="stroke-card" />
          <!-- Value labels (opt-in) -->
          <template v-if="showValues">
            <text
              v-for="point in line.dots"
              :key="`val-${line.taskId}-${point.i}`"
              :x="point.x"
              :y="Math.max(point.y - 7, 10)"
              text-anchor="middle"
              :fill="line.color"
              class="text-[9px] font-medium">
              {{ point.label }}
            </text>
          </template>
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

        <!-- Transparent hover bands, one per bucket, to drive the tooltip -->
        <rect
          v-for="band in geometry.hoverBands"
          :key="`band-${band.i}`"
          :x="band.x"
          :y="PAD.top"
          :width="band.width"
          :height="innerH"
          fill="transparent"
          class="cursor-crosshair"
          @mouseenter="activeIndex = band.i" />
      </svg>

      <!-- Floating tooltip -->
      <div
        v-if="tooltip"
        class="pointer-events-none absolute top-2 z-20 min-w-[9rem] rounded-xl border border-border bg-card/95 p-2.5 text-xs shadow-soft backdrop-blur-sm"
        :style="tooltipStyle">
        <p class="mb-1.5 font-semibold text-foreground">{{ tooltip.label }}</p>
        <ul v-if="tooltip.rows.length" class="space-y-1">
          <li
            v-for="row in tooltip.rows"
            :key="row.taskId"
            class="flex items-center gap-2">
            <span
              class="size-2 shrink-0 rounded-full"
              :style="{ backgroundColor: row.color }"></span>
            <span class="truncate text-muted-foreground">{{ row.name }}</span>
            <span class="ml-auto font-medium tabular-nums text-foreground">{{
              formatHours(row.hours)
            }}</span>
          </li>
        </ul>
        <p v-else class="text-muted-foreground">No time tracked.</p>
      </div>

      <div
        v-if="geometry.message"
        class="pointer-events-none absolute inset-0 flex items-center justify-center">
        <p class="text-sm text-muted-foreground">{{ geometry.message }}</p>
      </div>
    </div>

    <div
      v-if="tasks.length"
      class="mt-3 flex flex-wrap items-center justify-between gap-3">
      <!-- Legend: click to show/hide a task's line -->
      <div class="flex flex-wrap gap-x-4 gap-y-1.5">
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

      <!-- Toggle the on-point value labels -->
      <button
        class="flex shrink-0 items-center gap-1.5 text-xs font-medium transition-colors"
        :class="showValues ? 'text-primary' : 'text-muted-foreground hover:text-foreground'"
        :title="showValues ? 'Hide values' : 'Show values'"
        @click="showValues = !showValues">
        <Icon
          :name="showValues ? 'lucide:eye' : 'lucide:eye-off'"
          class="size-3.5" />
        Values
      </button>
    </div>
  </div>
</template>

<script setup>
  import { computed, reactive, ref } from "vue";

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
  const activeIndex = ref(null);
  const showValues = ref(false);

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

    const xByIndex = props.buckets.map((_, i) => xAt(i));

    const lines = visible.map(({ task, color }) => {
      const points = (task.series || []).map((hours, i) => ({
        i,
        x: xAt(i),
        y: yAt(hours),
        hours,
        label: formatHours(hours),
      }));
      return {
        taskId: task.task_id,
        name: task.task_name,
        color,
        path: points
          .map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
          .join(" "),
        points,
        dots: points.filter((p) => p.hours > 0),
      };
    });

    // A full-height band around each bucket so hovering anywhere in the column
    // (not just on a dot) reveals that bucket's values.
    const hoverBands = xByIndex.map((x, i) => {
      const left = i === 0 ? PAD.left : (xByIndex[i - 1] + x) / 2;
      const right =
        i === n - 1 ? W - PAD.right : (xByIndex[i + 1] + x) / 2;
      return { i, x: left, width: Math.max(right - left, 0) };
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

    return { lines, yTicks, xLabels, message, xByIndex, hoverBands };
  });

  // The values at the hovered bucket, biggest first, for the floating tooltip.
  const tooltip = computed(() => {
    if (activeIndex.value === null) return null;
    const i = activeIndex.value;
    const b = props.buckets[i];
    if (!b) return null;
    const rows = geometry.value.lines
      .map((line) => ({
        taskId: line.taskId,
        name: line.name,
        color: line.color,
        hours: line.points[i] ? line.points[i].hours : 0,
      }))
      .filter((row) => row.hours > 0)
      .sort((a, b) => b.hours - a.hours);
    return { label: labelAt(i), rows };
  });

  // Anchor the tooltip to the hovered column, nudging it inward near the edges
  // so it never spills out of the chart.
  const tooltipStyle = computed(() => {
    if (activeIndex.value === null) return {};
    const pct = (geometry.value.xByIndex[activeIndex.value] / W) * 100;
    let shift = "-50%";
    if (pct < 20) shift = "0%";
    else if (pct > 80) shift = "-100%";
    return { left: `${pct}%`, transform: `translateX(${shift})` };
  });

  function labelAt(i) {
    const b = props.buckets[i];
    return b ? formatBucketLabel(b.period_start, props.bucket) : "";
  }
</script>
