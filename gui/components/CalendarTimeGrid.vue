<template>
  <div class="overflow-hidden rounded-xl border border-border">
    <!-- Day headers -->
    <div class="grid border-b border-border bg-muted/30" :style="colsStyle">
      <div class="border-r border-border"></div>
      <div
        v-for="day in days"
        :key="dayKey(day)"
        class="border-r border-border px-2 py-2 text-center last:border-r-0">
        <div class="text-xs font-medium uppercase text-muted-foreground">
          {{ day.toLocaleDateString([], { weekday: "short" }) }}
        </div>
        <div
          class="mx-auto mt-0.5 flex size-7 items-center justify-center rounded-full text-sm font-semibold"
          :class="
            isToday(day) ? 'bg-primary text-primary-foreground' : 'text-foreground'
          ">
          {{ day.getDate() }}
        </div>
        <div
          v-if="trackedByDay[dayKey(day)]"
          class="mt-0.5 text-[10px] font-semibold text-accent">
          {{ compactDuration(trackedByDay[dayKey(day)]) }}
        </div>
      </div>
    </div>

    <!-- All-day strip -->
    <div
      v-if="hasAllDay"
      class="grid border-b border-border bg-background/40"
      :style="colsStyle">
      <div
        class="border-r border-border px-1 py-1 text-right text-[10px] uppercase text-muted-foreground">
        All day
      </div>
      <div
        v-for="day in days"
        :key="dayKey(day)"
        class="space-y-1 border-r border-border p-1 last:border-r-0">
        <button
          v-for="ev in layouts[dayKey(day)].allDay"
          :key="`${ev.id}-${ev.start}`"
          class="block w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] font-medium text-white"
          :style="{ backgroundColor: ev.color || '#007CBF' }"
          @click="emit('edit', ev)">
          {{ ev.recurrence ? "↻ " : "" }}{{ ev.title }}
        </button>
      </div>
    </div>

    <!-- Scrollable time grid -->
    <div ref="scroller" class="max-h-[62vh] overflow-y-auto">
      <div class="grid" :style="colsStyle">
        <!-- Hour gutter -->
        <div class="border-r border-border">
          <div
            v-for="hour in 24"
            :key="hour"
            class="relative border-t border-border/60 text-right"
            :style="{ height: `${HOUR_HEIGHT}px` }">
            <span class="pr-1 text-[10px] text-muted-foreground">
              {{ hourLabel(hour - 1) }}
            </span>
          </div>
        </div>

        <!-- Day columns -->
        <div
          v-for="day in days"
          :key="dayKey(day)"
          class="relative border-r border-border last:border-r-0"
          @click="createAt($event, day)">
          <div
            v-for="hour in 24"
            :key="hour"
            class="border-t border-border/60"
            :style="{ height: `${HOUR_HEIGHT}px` }"></div>

          <button
            v-for="seg in layouts[dayKey(day)].timed"
            :key="`${seg.event.id}-${seg.event.start}`"
            class="absolute overflow-hidden rounded-md px-1.5 py-0.5 text-left text-[11px] font-medium text-white shadow-soft"
            :style="blockStyle(seg)"
            :title="seg.event.title"
            @click.stop="emit('edit', seg.event)">
            <span class="block truncate">
              {{ seg.event.recurrence ? "↻ " : "" }}{{ seg.event.title }}
            </span>
            <span class="block truncate opacity-80">{{
              timeLabel(seg.event.start)
            }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted } from "vue";

  const props = defineProps({
    days: { type: Array, required: true },
    events: { type: Array, default: () => [] },
    timeEntries: { type: Array, default: () => [] },
  });

  const emit = defineEmits(["create", "edit"]);

  const HOUR_HEIGHT = 48;
  const scroller = ref(null);

  const colsStyle = computed(() => ({
    gridTemplateColumns: `3.5rem repeat(${props.days.length}, minmax(0, 1fr))`,
  }));

  // Pre-compute each day's all-day + timed layout, keyed by day.
  const layouts = computed(() => {
    const map = {};
    for (const day of props.days) {
      map[dayKey(day)] = dayEventLayout(props.events, day);
    }
    return map;
  });

  const hasAllDay = computed(() =>
    props.days.some((day) => layouts.value[dayKey(day)].allDay.length),
  );

  const trackedByDay = computed(() => {
    const map = {};
    for (const entry of props.timeEntries) {
      const start = new Date(entry.clock_in);
      const end = entry.clock_out ? new Date(entry.clock_out) : new Date();
      const key = dayKey(start);
      map[key] = (map[key] || 0) + (end - start);
    }
    return map;
  });

  function isToday(day) {
    return isSameDay(day, new Date());
  }

  function hourLabel(hour) {
    if (hour === 0) return "";
    return `${String(hour).padStart(2, "0")}:00`;
  }

  function timeLabel(value) {
    return new Date(value).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function compactDuration(ms) {
    const minutes = Math.round(ms / 60000);
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h && m) return `${h}h ${m}m`;
    if (h) return `${h}h`;
    return `${m}m`;
  }

  function blockStyle(seg) {
    const gap = 2;
    const width = 100 / seg.cols;
    return {
      top: `${(seg.startMin / 60) * HOUR_HEIGHT}px`,
      height: `${((seg.endMin - seg.startMin) / 60) * HOUR_HEIGHT - gap}px`,
      left: `calc(${seg.col * width}% + 2px)`,
      width: `calc(${width}% - 4px)`,
      backgroundColor: seg.event.color || "#007CBF",
    };
  }

  function createAt(e, day) {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const snapped = Math.round((y / HOUR_HEIGHT) * 2) * 30; // nearest 30 min
    const minutes = Math.max(0, Math.min(23 * 60 + 30, snapped));
    const date = new Date(day.getFullYear(), day.getMonth(), day.getDate());
    date.setMinutes(minutes);
    emit("create", date);
  }

  onMounted(() => {
    // Open scrolled to the start of the working day (07:00).
    if (scroller.value) scroller.value.scrollTop = 7 * HOUR_HEIGHT;
  });
</script>
