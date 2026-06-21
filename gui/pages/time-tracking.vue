<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">
        Time tracking
      </h1>
      <p class="mt-1 text-muted-foreground">
        Pick a subtask and clock in to start tracking.
      </p>
    </div>

    <div class="grid gap-6 lg:grid-cols-5">
      <!-- Task / subtask picker -->
      <div class="lg:col-span-3">
        <UiCard title="Your tasks">
          <template #actions>
            <UiButton size="sm" icon="lucide:plus" @click="openAddTaskDialog"
              >Add task</UiButton
            >
          </template>

          <div
            v-if="loadingTasks"
            class="flex items-center justify-center py-12 text-muted-foreground">
            <Icon name="lucide:loader-circle" class="size-6 animate-spin" />
          </div>

          <div
            v-else-if="!tasks.length"
            class="flex flex-col items-center gap-3 py-12 text-center">
            <div
              class="flex size-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
              <Icon name="lucide:folder-plus" class="size-6" />
            </div>
            <div>
              <p class="font-medium">No tasks yet</p>
              <p class="text-sm text-muted-foreground">
                Create your first task to start tracking time.
              </p>
            </div>
            <UiButton size="sm" icon="lucide:plus" @click="openAddTaskDialog"
              >Add task</UiButton
            >
          </div>

          <ul v-else class="space-y-2">
            <li
              v-for="task in tasks"
              :key="task.id"
              class="overflow-hidden rounded-xl border border-border">
              <button
                class="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted"
                @click="toggleExpand(task.id)">
                <Icon
                  name="lucide:chevron-right"
                  class="size-4 text-muted-foreground transition-transform"
                  :class="{ 'rotate-90': isExpanded(task.id) }" />
                <Icon name="lucide:folder" class="size-[18px] text-primary" />
                <span class="flex-1 font-medium">{{ task.name }}</span>
                <span
                  class="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {{ task.subtasks.length }} subtask{{
                    task.subtasks.length === 1 ? "" : "s"
                  }}
                </span>
              </button>

              <div
                v-if="isExpanded(task.id)"
                class="border-t border-border bg-background/40 px-3 py-2">
                <button
                  v-for="subtask in task.subtasks"
                  :key="subtask.id"
                  class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors"
                  :class="
                    isSelected(task, subtask)
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted'
                  "
                  @click="selectSubtask(subtask, task)">
                  <Icon
                    :name="
                      isSelected(task, subtask)
                        ? 'lucide:circle-check-big'
                        : 'lucide:circle'
                    "
                    class="size-[18px] shrink-0" />
                  <span class="flex-1">
                    <span class="font-medium">{{ subtask.name }}</span>
                    <span
                      v-if="subtask.description"
                      class="ml-2 text-muted-foreground"
                      >{{ subtask.description }}</span
                    >
                  </span>
                </button>

                <p
                  v-if="!task.subtasks.length"
                  class="px-3 py-2 text-sm text-muted-foreground">
                  No subtasks yet.
                </p>

                <UiButton
                  variant="ghost"
                  size="sm"
                  icon="lucide:plus"
                  class="mt-1 w-full justify-start"
                  @click="openAddSubTaskDialog(task)">
                  Add subtask
                </UiButton>
              </div>
            </li>
          </ul>
        </UiCard>
      </div>

      <!-- Tracker -->
      <div class="lg:col-span-2">
        <UiCard title="Tracker" class="lg:sticky lg:top-6">
          <!-- Active session -->
          <div v-if="isClockedIn && clockInTime" class="space-y-5">
            <div class="rounded-2xl bg-accent/10 p-5 text-center">
              <p class="text-sm text-muted-foreground">Tracking</p>
              <p class="mt-1 font-semibold">{{ activeTask?.name }}</p>
              <p class="text-sm text-muted-foreground">
                {{ activeSubTask?.name }}
              </p>
              <p
                class="mt-4 font-mono text-4xl font-bold tabular-nums tracking-tight">
                {{ clockInDuration }}
              </p>
              <p class="mt-1 text-xs text-muted-foreground">
                Started at {{ clockInTime.toLocaleTimeString() }}
              </p>
            </div>

            <UiButton
              variant="danger"
              block
              size="lg"
              icon="lucide:square"
              @click="clockOut">
              Clock out
            </UiButton>

            <div v-if="recentTimeEntries.length">
              <p class="mb-2 text-sm font-medium text-muted-foreground">
                Recent entries (24h)
              </p>
              <ul class="space-y-1.5">
                <li
                  v-for="entry in recentTimeEntries"
                  :key="entry.id"
                  class="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
                  <span
                    >{{ formatClock(entry.clock_in) }} –
                    {{
                      entry.clock_out ? formatClock(entry.clock_out) : "ongoing"
                    }}</span
                  >
                  <Icon
                    :name="
                      entry.clock_out ? 'lucide:check' : 'lucide:loader-circle'
                    "
                    class="size-4 text-muted-foreground"
                    :class="{ 'animate-spin': !entry.clock_out }" />
                </li>
              </ul>
            </div>
          </div>

          <!-- Idle -->
          <div v-else class="space-y-5">
            <div
              v-if="selectedSubtask"
              class="rounded-2xl bg-muted p-5 text-center">
              <p class="text-sm text-muted-foreground">Selected</p>
              <p class="mt-1 font-semibold">{{ selectedTask?.name }}</p>
              <p class="text-sm text-muted-foreground">
                {{ selectedSubtask.name }}
              </p>
            </div>
            <div
              v-else
              class="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-border p-8 text-center text-muted-foreground">
              <Icon name="lucide:mouse-pointer-click" class="size-7" />
              <p class="text-sm">Select a subtask to begin.</p>
            </div>

            <UiButton
              block
              size="lg"
              icon="lucide:play"
              :disabled="!canClockIn"
              @click="clockIn">
              Clock in
            </UiButton>
          </div>
        </UiCard>
      </div>
    </div>

    <AddTaskDialog
      v-model="dialogAddTaskVisible"
      @task-created="handleTaskCreated" />
    <AddSubTaskDialog
      v-if="currentTaskForSubtask"
      v-model="dialogAddSubTaskVisible"
      :task-id="currentTaskForSubtask.id"
      @subtask-created="handleSubTaskCreated" />
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, onBeforeUnmount } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { $api } = useNuxtApp();

  const tasks = ref([]);
  const loadingTasks = ref(false);
  const expanded = ref([]);

  const selectedTask = ref(null);
  const selectedSubtask = ref(null);
  const activeTask = ref(null);
  const activeSubTask = ref(null);
  const isClockedIn = ref(false);

  const clockInTime = ref(null);
  const clockInDuration = ref("00:00:00");
  let clockInterval = null;
  const activeTimeEntryId = ref(null);
  const recentTimeEntries = ref([]);

  const dialogAddTaskVisible = ref(false);
  const dialogAddSubTaskVisible = ref(false);
  const currentTaskForSubtask = ref(null);

  onMounted(async () => {
    loadingTasks.value = true;
    try {
      tasks.value = await $api("/ticktask/user/get-tasks-and-subtasks/", {
        method: "GET",
      });

      const active = await $api("/ticktask/user/get-clocked-in-time-entry/", {
        method: "GET",
      });
      if (active) {
        const subtask = active.subtasks[0];
        const entry = subtask.time_entries[0];

        selectedTask.value = active;
        activeTask.value = active;
        selectedSubtask.value = subtask;
        activeSubTask.value = subtask;
        activeTimeEntryId.value = entry.id;
        isClockedIn.value = true;
        clockInTime.value = new Date(entry.clock_in);
        expanded.value = [active.id];
        startClockInTimer();
        fetchRecentTimeEntries(subtask.id);
      }
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      loadingTasks.value = false;
    }
  });

  const canClockIn = computed(
    () => !!selectedTask.value && !!selectedSubtask.value && !isClockedIn.value,
  );

  function isExpanded(taskId) {
    return expanded.value.includes(taskId);
  }

  function toggleExpand(taskId) {
    expanded.value = isExpanded(taskId)
      ? expanded.value.filter((id) => id !== taskId)
      : [...expanded.value, taskId];
  }

  function isSelected(task, subtask) {
    return (
      selectedTask.value?.id === task.id &&
      selectedSubtask.value?.id === subtask.id
    );
  }

  function selectSubtask(subtask, task) {
    selectedTask.value = task;
    selectedSubtask.value = subtask;
  }

  async function clockIn() {
    try {
      const existing = await $api("/ticktask/user/get-clocked-in-time-entry/", {
        method: "GET",
      });
      if (existing) {
        alert(
          "You already have an active task. Please close it before starting a new one.",
        );
        return;
      }

      const response = await $api("/ticktask/user/clock-in/", {
        method: "POST",
        body: { subtask_id: selectedSubtask.value.id },
      });

      isClockedIn.value = true;
      clockInTime.value = new Date(response.clock_in);
      activeTimeEntryId.value = response.id;
      activeTask.value = selectedTask.value;
      activeSubTask.value = selectedSubtask.value;
      startClockInTimer();
      fetchRecentTimeEntries(activeSubTask.value.id);
    } catch (err) {
      console.error("Error during clock in:", err);
    }
  }

  async function clockOut() {
    try {
      await $api("/ticktask/user/clock-out/", {
        method: "POST",
        body: { entity_id: activeTimeEntryId.value },
      });

      isClockedIn.value = false;
      if (clockInterval) clearInterval(clockInterval);

      clockInTime.value = null;
      clockInDuration.value = "00:00:00";
      activeTimeEntryId.value = null;
      activeTask.value = null;
      activeSubTask.value = null;
      recentTimeEntries.value = [];
    } catch (err) {
      console.error("Error during clock out:", err);
    }
  }

  async function fetchRecentTimeEntries(subtaskId) {
    try {
      recentTimeEntries.value = await $api("/ticktask/user/get-time-entries/", {
        method: "POST",
        body: { subtask_id: subtaskId, last_hours: 24 },
      });
    } catch (err) {
      console.error("Error fetching recent time entries:", err);
      recentTimeEntries.value = [];
    }
  }

  function startClockInTimer() {
    if (clockInterval) clearInterval(clockInterval);
    clockInterval = setInterval(() => {
      clockInDuration.value = formatDuration(new Date() - clockInTime.value);
    }, 1000);
  }

  function openAddTaskDialog() {
    dialogAddTaskVisible.value = true;
  }

  function handleTaskCreated(task) {
    tasks.value.push({ ...task, subtasks: task.subtasks ?? [] });
    expanded.value = [...expanded.value, task.id];
  }

  function openAddSubTaskDialog(task) {
    currentTaskForSubtask.value = task;
    dialogAddSubTaskVisible.value = true;
  }

  function handleSubTaskCreated(newSubtask) {
    const task = tasks.value.find(
      (t) => t.id === currentTaskForSubtask.value.id,
    );
    if (task)
      task.subtasks.push({
        ...newSubtask,
        time_entries: newSubtask.time_entries ?? [],
      });
  }

  onBeforeUnmount(() => {
    if (clockInterval) clearInterval(clockInterval);
  });
</script>
