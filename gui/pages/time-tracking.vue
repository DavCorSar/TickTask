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
              <div class="flex items-center">
                <button
                  class="flex flex-1 items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted"
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
                <button
                  class="px-3 py-3 text-muted-foreground transition-colors hover:text-danger"
                  title="Delete task"
                  @click="askDeleteTask(task)">
                  <Icon name="lucide:trash-2" class="size-4" />
                </button>
              </div>

              <div
                v-if="isExpanded(task.id)"
                class="border-t border-border bg-background/40 px-3 py-2">
                <div
                  v-for="subtask in task.subtasks"
                  :key="subtask.id"
                  class="group flex items-center gap-1 rounded-lg transition-colors"
                  :class="
                    isSelected(task, subtask)
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted'
                  ">
                  <button
                    class="flex flex-1 items-center gap-3 px-3 py-2.5 text-left text-sm"
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
                  <button
                    class="px-2.5 py-2.5 text-muted-foreground opacity-0 transition-opacity hover:text-danger focus:opacity-100 group-hover:opacity-100"
                    title="Delete subtask"
                    @click="askDeleteSubtask(task, subtask)">
                    <Icon name="lucide:trash-2" class="size-4" />
                  </button>
                </div>

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

    <UiConfirmDialog
      v-model="confirmOpen"
      title="Delete"
      :message="confirmMessage"
      confirm-label="Delete"
      :loading="confirmLoading"
      @confirm="confirmDelete" />
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, onBeforeUnmount } from "vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const {
    fetchTasks,
    getClockedIn,
    clockIn: apiClockIn,
    clockOut: apiClockOut,
    getTimeEntries,
    deleteTask: apiDeleteTask,
    deleteSubtask: apiDeleteSubtask,
  } = useTasks();
  const toast = useToast();

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

  const confirmOpen = ref(false);
  const confirmLoading = ref(false);
  const pendingDelete = ref(null);

  const confirmMessage = computed(() => {
    if (!pendingDelete.value) return "";
    if (pendingDelete.value.kind === "task") {
      return (
        `Delete "${pendingDelete.value.task.name}"? It disappears from time ` +
        "tracking but its tracked time stays on the dashboard and calendar, " +
        "and you can restore it later."
      );
    }
    return (
      `Delete subtask "${pendingDelete.value.subtask.name}"? It disappears ` +
      "from time tracking but its tracked time is kept, and you can restore it later."
    );
  });

  onMounted(async () => {
    loadingTasks.value = true;
    try {
      tasks.value = await fetchTasks();

      const active = await getClockedIn();
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
      toast.error("Couldn't load your tasks.");
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
      const existing = await getClockedIn();
      if (existing) {
        toast.info(
          "You already have an active task. Clock it out before starting a new one.",
        );
        return;
      }

      const response = await apiClockIn(selectedSubtask.value.id);

      isClockedIn.value = true;
      clockInTime.value = new Date(response.clock_in);
      activeTimeEntryId.value = response.id;
      activeTask.value = selectedTask.value;
      activeSubTask.value = selectedSubtask.value;
      startClockInTimer();
      fetchRecentTimeEntries(activeSubTask.value.id);
    } catch (err) {
      console.error("Error during clock in:", err);
      toast.error(err?.data?.detail || "Couldn't clock in.");
    }
  }

  async function clockOut() {
    try {
      await apiClockOut(activeTimeEntryId.value);
      resetTracker();
    } catch (err) {
      console.error("Error during clock out:", err);
      toast.error("Couldn't clock out.");
    }
  }

  async function fetchRecentTimeEntries(subtaskId) {
    try {
      recentTimeEntries.value = await getTimeEntries(subtaskId, 24);
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
    toast.success(`Task "${task.name}" created.`);
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
    toast.success(`Subtask "${newSubtask.name}" created.`);
  }

  function resetTracker() {
    isClockedIn.value = false;
    if (clockInterval) clearInterval(clockInterval);
    clockInTime.value = null;
    clockInDuration.value = "00:00:00";
    activeTimeEntryId.value = null;
    activeTask.value = null;
    activeSubTask.value = null;
    recentTimeEntries.value = [];
  }

  function askDeleteTask(task) {
    pendingDelete.value = { kind: "task", task };
    confirmOpen.value = true;
  }

  function askDeleteSubtask(task, subtask) {
    pendingDelete.value = { kind: "subtask", task, subtask };
    confirmOpen.value = true;
  }

  async function confirmDelete() {
    if (!pendingDelete.value || confirmLoading.value) return;
    confirmLoading.value = true;
    try {
      const { kind, task, subtask } = pendingDelete.value;
      if (kind === "task") {
        await apiDeleteTask(task.id);
        tasks.value = tasks.value.filter((t) => t.id !== task.id);
        if (selectedTask.value?.id === task.id) {
          selectedTask.value = null;
          selectedSubtask.value = null;
        }
        if (activeTask.value?.id === task.id) resetTracker();
        toast.success(`Task "${task.name}" deleted.`);
      } else {
        await apiDeleteSubtask(subtask.id);
        const parent = tasks.value.find((t) => t.id === task.id);
        if (parent)
          parent.subtasks = parent.subtasks.filter((s) => s.id !== subtask.id);
        if (selectedSubtask.value?.id === subtask.id)
          selectedSubtask.value = null;
        if (activeSubTask.value?.id === subtask.id) resetTracker();
        toast.success(`Subtask "${subtask.name}" deleted.`);
      }
      confirmOpen.value = false;
      pendingDelete.value = null;
    } catch (err) {
      console.error("Error deleting:", err);
      toast.error(err?.data?.detail || "Couldn't delete. Please try again.");
    } finally {
      confirmLoading.value = false;
    }
  }

  onBeforeUnmount(() => {
    if (clockInterval) clearInterval(clockInterval);
  });
</script>
