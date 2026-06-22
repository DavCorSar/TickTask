<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Calendar</h1>
        <p class="mt-1 text-muted-foreground">Your tracked time and scheduled events.</p>
      </div>
      <UiButton icon="lucide:plus" @click="openCreate(new Date())">New event</UiButton>
    </div>

    <UiCard padded>
      <!-- Toolbar -->
      <div class="mb-4 flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <UiButton variant="outline" size="icon" icon="lucide:chevron-left" @click="prevMonth" />
          <UiButton variant="outline" size="icon" icon="lucide:chevron-right" @click="nextMonth" />
          <UiButton variant="ghost" size="sm" @click="goToday">Today</UiButton>
        </div>
        <h2 class="text-lg font-semibold capitalize">{{ monthLabel(cursor) }}</h2>
        <div class="w-[88px]"></div>
      </div>

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
          <Icon name="lucide:loader-circle" class="size-6 animate-spin text-muted-foreground" />
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
              class="rounded-full bg-accent/15 px-1.5 py-0.5 text-[10px] font-semibold text-accent">
              {{ compactDuration(trackedByDay[dayKey(day)]) }}
            </span>
          </div>

          <div class="relative z-10 mt-1 space-y-1">
            <button
              v-for="ev in (eventsByDay[dayKey(day)] || []).slice(0, 3)"
              :key="ev.id"
              class="flex w-full items-center rounded-md px-1.5 py-0.5 text-left text-[11px] font-medium text-white"
              :style="{ backgroundColor: ev.color || '#007CBF' }"
              @click.stop="openEdit(ev)">
              <span class="truncate">{{ ev.title }}</span>
            </button>
            <span
              v-if="(eventsByDay[dayKey(day)] || []).length > 3"
              class="block px-1.5 text-[10px] text-muted-foreground">
              +{{ eventsByDay[dayKey(day)].length - 3 }} more
            </span>
          </div>
        </div>
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

  const { $api } = useNuxtApp();

  const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const cursor = ref(new Date());
  const events = ref([]);
  const timeEntries = ref([]);
  const loading = ref(false);

  const dialogOpen = ref(false);
  const editingEvent = ref(null);
  const defaultStart = ref(null);

  const days = computed(() => buildMonthMatrix(cursor.value));

  const eventsByDay = computed(() => {
    const map = {};
    for (const ev of events.value) {
      (map[dayKey(ev.start)] ||= []).push(ev);
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
        59
      );

      const res = await $api("/calendar/user/get-calendar/", {
        method: "GET",
        query: { start: first.toISOString(), end: rangeEnd.toISOString() },
      });
      events.value = res.events;
      timeEntries.value = res.time_entries;
    } catch (err) {
      console.error("Error loading calendar:", err);
    } finally {
      loading.value = false;
    }
  }

  function prevMonth() {
    cursor.value = addMonths(cursor.value, -1);
  }

  function nextMonth() {
    cursor.value = addMonths(cursor.value, 1);
  }

  function goToday() {
    cursor.value = new Date();
  }

  function openCreate(day) {
    editingEvent.value = null;
    const d = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 9, 0);
    defaultStart.value = d.toISOString();
    dialogOpen.value = true;
  }

  function openEdit(ev) {
    editingEvent.value = ev;
    defaultStart.value = null;
    dialogOpen.value = true;
  }

  watch(cursor, load, { immediate: true });
</script>
