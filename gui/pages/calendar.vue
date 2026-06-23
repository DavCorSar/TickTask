<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Calendar</h1>
        <p class="mt-1 text-muted-foreground">
          Your tracked time and scheduled events.
        </p>
      </div>
      <div class="flex items-center gap-4">
        <label
          class="flex cursor-pointer select-none items-center gap-2 text-sm text-muted-foreground">
          <input
            v-model="includeDeleted"
            type="checkbox"
            class="size-4 rounded border-border accent-primary" />
          Show deleted
        </label>
        <UiButton icon="lucide:plus" @click="openCreate(new Date())"
          >New event</UiButton
        >
      </div>
    </div>

    <UiCard padded>
      <!-- Toolbar -->
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <UiButton
            variant="outline"
            size="icon"
            icon="lucide:chevron-left"
            @click="goPrev" />
          <UiButton
            variant="outline"
            size="icon"
            icon="lucide:chevron-right"
            @click="goNext" />
          <UiButton variant="ghost" size="sm" @click="goToday">Today</UiButton>
        </div>
        <h2 class="text-lg font-semibold capitalize">{{ title }}</h2>
        <div class="inline-flex rounded-xl border border-border p-0.5">
          <button
            v-for="option in views"
            :key="option"
            class="rounded-lg px-3 py-1 text-sm font-medium capitalize transition-colors"
            :class="
              view === option
                ? 'bg-primary text-primary-foreground shadow-soft'
                : 'text-muted-foreground hover:text-foreground'
            "
            @click="view = option">
            {{ option }}
          </button>
        </div>
      </div>

      <!-- Month view -->
      <template v-if="view === 'month'">
      <!-- Weekday headers -->
      <div class="grid grid-cols-7 gap-1.5 pb-1.5">
        <div
          v-for="weekday in weekdays"
          :key="weekday"
          class="px-1 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {{ weekday }}
        </div>
      </div>

      <!-- Day grid -->
      <div class="relative grid grid-cols-7 gap-1.5">
        <div
          v-if="loading"
          class="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
          <Icon
            name="lucide:loader-circle"
            class="size-6 animate-spin text-muted-foreground" />
        </div>

        <div
          v-for="day in days"
          :key="day.toISOString()"
          class="relative min-h-[7rem] rounded-xl border border-border p-1.5"
          :class="isSameMonth(day, cursor) ? 'bg-card' : 'bg-muted/40'">
          <button
            class="absolute inset-0 z-0 rounded-xl transition-colors hover:bg-muted/50"
            aria-label="Add event on this day"
            @click="openCreate(day)"></button>

          <div class="relative z-10 flex items-center justify-between">
            <span
              class="flex size-6 items-center justify-center rounded-full text-xs font-medium"
              :class="
                isToday(day)
                  ? 'bg-primary text-primary-foreground'
                  : isSameMonth(day, cursor)
                    ? 'text-foreground'
                    : 'text-muted-foreground'
              ">
              {{ day.getDate() }}
            </span>
            <span
              v-if="trackedByDay[dayKey(day)]"
              class="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
              :class="
                deletedByDay[dayKey(day)]
                  ? 'bg-muted text-muted-foreground'
                  : 'bg-accent/15 text-accent'
              "
              :title="
                deletedByDay[dayKey(day)] ? 'Includes deleted tracked time' : ''
              ">
              {{ compactDuration(trackedByDay[dayKey(day)]) }}
            </span>
          </div>

          <div class="relative z-10 mt-1 space-y-1">
            <button
              v-for="seg in (eventsByDay[dayKey(day)] || []).slice(0, 3)"
              :key="seg.event.id"
              class="flex min-h-[1.1rem] w-full items-center px-1.5 py-0.5 text-left text-[11px] font-medium text-white"
              :class="[
                seg.isStart || day.getDay() === 1 ? 'rounded-l-md' : '',
                seg.isEnd || day.getDay() === 0 ? 'rounded-r-md' : '',
              ]"
              :style="{ backgroundColor: seg.event.color || '#007CBF' }"
              :title="seg.event.title"
              @click.stop="openEdit(seg.event)">
              <span class="truncate">
                {{
                  seg.isStart || day.getDay() === 1
                    ? (seg.event.recurrence ? "↻ " : "") + seg.event.title
                    : ""
                }}
              </span>
            </button>
            <span
              v-if="(eventsByDay[dayKey(day)] || []).length > 3"
              class="block px-1.5 text-[10px] text-muted-foreground">
              +{{ eventsByDay[dayKey(day)].length - 3 }} more
            </span>
          </div>
        </div>
      </div>
      </template>

      <!-- Week / Day view -->
      <div v-else class="relative">
        <div
          v-if="loading"
          class="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-card/60 backdrop-blur-sm">
          <Icon
            name="lucide:loader-circle"
            class="size-6 animate-spin text-muted-foreground" />
        </div>
        <CalendarTimeGrid
          :days="days"
          :events="events"
          :time-entries="timeEntries"
          @create="openCreateAt"
          @edit="openEdit" />
      </div>
    </UiCard>

    <EventDialog
      v-model="dialogOpen"
      :event="editingEvent"
      :default-start="defaultStart"
      @saved="load"
      @deleted="load" />
  </div>
</template>

<script setup>
  import { ref, computed, watch } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { getCalendar } = useCalendar();
  const toast = useToast();

  const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const views = ["month", "week", "day"];
  const view = ref("month");
  const cursor = ref(new Date());
  const events = ref([]);
  const timeEntries = ref([]);
  const loading = ref(false);
  const includeDeleted = ref(false);

  const dialogOpen = ref(false);
  const editingEvent = ref(null);
  const defaultStart = ref(null);

  const days = computed(() => {
    if (view.value === "week") return weekDays(cursor.value);
    if (view.value === "day") {
      const c = cursor.value;
      return [new Date(c.getFullYear(), c.getMonth(), c.getDate())];
    }
    return buildMonthMatrix(cursor.value);
  });

  const title = computed(() => {
    if (view.value === "day") {
      return cursor.value.toLocaleDateString([], {
        weekday: "long",
        month: "long",
        day: "numeric",
      });
    }
    if (view.value === "week") {
      const ds = days.value;
      const fmt = (d) =>
        d.toLocaleDateString([], { month: "short", day: "numeric" });
      return `${fmt(ds[0])} – ${fmt(ds[ds.length - 1])}`;
    }
    return monthLabel(cursor.value);
  });

  const eventsByDay = computed(() => {
    const map = eventSegmentsByDay(events.value, days.value);
    for (const key in map) {
      map[key].sort((a, b) => new Date(a.event.start) - new Date(b.event.start));
    }
    return map;
  });

  const trackedByDay = computed(() => {
    const map = {};
    for (const entry of timeEntries.value) {
      const start = new Date(entry.clock_in);
      const end = entry.clock_out ? new Date(entry.clock_out) : new Date();
      const key = dayKey(start);
      map[key] = (map[key] || 0) + (end - start);
    }
    return map;
  });

  const deletedByDay = computed(() => {
    const map = {};
    for (const entry of timeEntries.value) {
      if (entry.deleted) map[dayKey(new Date(entry.clock_in))] = true;
    }
    return map;
  });

  function isToday(day) {
    return isSameDay(day, new Date());
  }

  function compactDuration(ms) {
    const minutes = Math.round(ms / 60000);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours && mins) return `${hours}h ${mins}m`;
    if (hours) return `${hours}h`;
    return `${mins}m`;
  }

  async function load() {
    loading.value = true;
    try {
      const first = days.value[0];
      const last = days.value[days.value.length - 1];
      const rangeEnd = new Date(
        last.getFullYear(),
        last.getMonth(),
        last.getDate(),
        23,
        59,
        59,
      );

      const res = await getCalendar(
        first.toISOString(),
        rangeEnd.toISOString(),
        includeDeleted.value,
      );
      events.value = res.events;
      timeEntries.value = res.time_entries;
    } catch (err) {
      console.error("Error loading calendar:", err);
      toast.error("Couldn't load the calendar.");
    } finally {
      loading.value = false;
    }
  }

  function shift(amount) {
    if (view.value === "week") cursor.value = addWeeks(cursor.value, amount);
    else if (view.value === "day") cursor.value = addDays(cursor.value, amount);
    else cursor.value = addMonths(cursor.value, amount);
  }

  function goPrev() {
    shift(-1);
  }

  function goNext() {
    shift(1);
  }

  function goToday() {
    cursor.value = new Date();
  }

  function openCreate(day) {
    // Month view: a day cell → default to 9:00 on that day.
    const d = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 9, 0);
    openCreateAt(d);
  }

  function openCreateAt(date) {
    // Week/day view: an exact clicked time.
    editingEvent.value = null;
    defaultStart.value = date.toISOString();
    dialogOpen.value = true;
  }

  function openEdit(ev) {
    editingEvent.value = ev;
    defaultStart.value = null;
    dialogOpen.value = true;
  }

  watch(cursor, load, { immediate: true });
  watch(view, load);
  watch(includeDeleted, load);
</script>
