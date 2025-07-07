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
                selectedTask?.id === item.id,
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
              </v-data-table>
            </td>
          </tr>
        </template>
      </v-data-table>

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
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from "vue";

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
    selectedTask.value = task;
    selectedSubtask.value = subtask;
  }

  function clockIn() {
    isClockedIn.value = true;
    console.log(
      `Clocked in to ${selectedTask.value.name} > ${selectedSubtask.value.name}`
    );
  }

  function clockOut() {
    isClockedIn.value = false;
    console.log(
      `Clocked out from ${selectedTask.value.name} > ${selectedSubtask.value.name}`
    );
  }
</script>
