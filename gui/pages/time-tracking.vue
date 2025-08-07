<template>
  <v-container>
    <v-card class="pa-4" elevation="2">
      <v-card-title>Select a Task</v-card-title>

      <v-data-table
        :headers="taskHeaders"
        :items="tasks"
        item-value="id"
        :items-per-page="5"
        :hide-default-footer="true"
        :loading="loadingTasks"
        class="mb-6 rounded-lg elevation-1"
        dense
        hover
        show-expand
        expand-on-click
        v-model:expanded="expanded">
        <template #item.name="{ item }">
          <span
            @click="selectTask(item)"
            :class="{
              'text-blue-darken-3 font-weight-bold':
                selectedTask?.id === item.id && selectSubtask,
            }">
            {{ item.name }}
          </span>
        </template>

        <template #expanded-row="{ item }">
          <tr>
            <td :colspan="taskHeaders.length">
              <v-data-table
                :headers="subtaskHeaders"
                :items="item.subtasks"
                item-value="id"
                dense
                hide-default-footer
                class="rounded-lg elevation-0">
                <template #item.name="{ item: subtask }">
                  <span
                    @click.stop="selectSubtask(subtask, item)"
                    :class="{
                      'text-green-darken-3 font-weight-bold':
                        selectedSubtask?.id === subtask.id &&
                        selectedTask?.id === item.id,
                    }"
                    style="cursor: pointer">
                    {{ subtask.name }}
                  </span>
                </template>

                <template #body.append>
                  <tr>
                    <td :colspan="subtaskHeaders.length">
                      <v-btn
                        color="primary"
                        @click="openAddSubTaskDialog(item)"
                        block>
                        ➕ Add Subtask
                      </v-btn>
                    </td>
                  </tr>
                </template>
              </v-data-table>
            </td>
          </tr>
        </template>

        <template #body.append>
          <tr>
            <td :colspan="taskHeaders.length">
              <v-btn
                color="primary"
                @click="openAddTaskDialog"
                variant="flat"
                block>
                ➕ Add Task
              </v-btn>
            </td>
          </tr>
        </template>
      </v-data-table>

      <v-row v-if="isClockedIn && clockInTime" class="mt-2" justify="center">
        <v-col cols="12" class="text-center">
          <v-alert type="success" variant="tonal">
            ⏰ <strong>Clocked in at:</strong>
            {{ clockInTime.toLocaleTimeString() }}<br />
            ⏳ <strong>Time elapsed:</strong> {{ clockInDuration }}
          </v-alert>
        </v-col>
      </v-row>
      <v-row
        v-if="selectedTask && selectedSubtask"
        class="mt-6"
        justify="center">
        <v-btn
          color="success"
          class="ma-2"
          :disabled="!canClockIn"
          @click="clockIn">
          ✅ Clock In
        </v-btn>
        <v-btn
          color="error"
          class="ma-2"
          :disabled="!canClockOut"
          @click="clockOut">
          ❌ Clock Out
        </v-btn>
      </v-row>
    </v-card>
    <v-row v-if="selectedTask && selectedSubtask" class="mt-6" justify="center">
      <v-col cols="12" class="text-center">
        <v-alert type="info" variant="tonal">
          <strong>Selected Task:</strong> {{ selectedTask.name }}<br />
          <strong>Selected Subtask:</strong> {{ selectedSubtask.name }}
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
  <AddTaskDialog
    v-model="dialogAddTaskVisible"
    @task-created="handleTaskCreated" />

  <AddSubTaskDialog
    v-if="currentTaskForSubtask"
    v-model="dialogAddSubTaskVisible"
    :task-id="currentTaskForSubtask.id"
    @subtask-created="handleSubTaskCreated" />
</template>

<script setup>
  import { ref, computed, onMounted, onBeforeUnmount } from "vue";
  import AddTaskDialog from "~/components/AddTaskDialog.vue";
  import AddSubTaskDialog from "~/components/AddSubTaskDialog.vue";

  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });

  const { $api } = useNuxtApp();

  const tasks = ref([]);
  const taskHeaders = [{ text: "Task", value: "name" }];
  const subtaskHeaders = [{ text: "Subtask", value: "name" }];

  const selectedTask = ref(null);
  const selectedSubtask = ref(null);
  const isClockedIn = ref(false);
  const loadingTasks = ref(false);
  const dialogAddTaskVisible = ref(false);
  const dialogAddSubTaskVisible = ref(false);
  const currentTaskForSubtask = ref(null);

  const clockInTime = ref(null);
  const clockInDuration = ref("00:00:00");
  let clockInterval = null;
  const activeTimeEntryId = ref(null);

  const expanded = ref([]);

  onMounted(async () => {
    loadingTasks.value = true;
    try {
      const response = await $api("/ticktask/user/get-tasks-and-subtasks/", {
        method: "GET",
      });
      tasks.value = response;
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      loadingTasks.value = false;
    }
  });

  const canClockIn = computed(
    () => selectedTask.value && selectedSubtask.value && !isClockedIn.value
  );
  const canClockOut = computed(
    () => selectedTask.value && selectedSubtask.value && isClockedIn.value
  );

  function selectTask(task) {
    selectedTask.value = task;
    selectedSubtask.value = null;
  }

  function selectSubtask(subtask, task) {
    // TODO(David): Show the time entries of this task during the current day
    selectedTask.value = task;
    selectedSubtask.value = subtask;
  }

  async function clockIn() {
    try {
      const response = await $api("/ticktask/user/clock-in/", {
        method: "POST",
        body: {
          subtask_id: selectedSubtask.value.id,
        },
      });

      isClockedIn.value = true;
      clockInTime.value = new Date(response.clock_in);
      activeTimeEntryId.value = response.id;
      startClockInTimer();
    } catch (err) {
      console.error("Error during clock in:", err);
    }
  }

  async function clockOut() {
    try {
      console.log("entry id: ", activeTimeEntryId.value);
      const response = await $api("/ticktask/user/clock-out/", {
        method: "POST",
        body: {
          entity_id: activeTimeEntryId.value,
        },
      });

      isClockedIn.value = false;
      if (clockInterval) clearInterval(clockInterval);

      clockInTime.value = null;
      clockInDuration.value = "00:00:00";
      activeTimeEntryId.value = null;
    } catch (err) {
      console.error("Error during clock out:", err);
    }
  }

  function startClockInTimer() {
    if (clockInterval) clearInterval(clockInterval);

    clockInterval = setInterval(() => {
      const now = new Date();
      const diff = now - clockInTime.value; // en ms

      const hours = String(Math.floor(diff / 3600000)).padStart(2, "0");
      const minutes = String(Math.floor((diff % 3600000) / 60000)).padStart(
        2,
        "0"
      );
      const seconds = String(Math.floor((diff % 60000) / 1000)).padStart(
        2,
        "0"
      );

      clockInDuration.value = `${hours}:${minutes}:${seconds}`;
    }, 1000);
  }

  const openAddTaskDialog = () => {
    dialogAddTaskVisible.value = true;
  };

  const handleTaskCreated = (task) => {
    tasks.value.push(task);
  };

  function openAddSubTaskDialog(task) {
    currentTaskForSubtask.value = task;
    dialogAddSubTaskVisible.value = true;
  }

  function handleSubTaskCreated(newSubtask) {
    const task = tasks.value.find(
      (t) => t.id === currentTaskForSubtask.value.id
    );
    if (task) {
      task.subtasks.push(newSubtask);
    }
  }

  onBeforeUnmount(() => {
    if (clockInterval) clearInterval(clockInterval);
  });
</script>
