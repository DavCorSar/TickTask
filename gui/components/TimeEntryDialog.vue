<template>
  <UiModal v-model="open" :title="isEdit ? 'Edit time entry' : 'Add time entry'">
    <form id="entry-form" class="space-y-4" @submit.prevent="submit">
      <!-- Subtask: pickable on create, read-only on edit -->
      <div v-if="isEdit">
        <span class="mb-1.5 block text-sm font-medium">Subtask</span>
        <p class="rounded-xl border border-border bg-muted px-3.5 py-2.5 text-sm">
          {{ entry.task_name }} › {{ entry.subtask_name }}
        </p>
      </div>
      <template v-else>
        <div>
          <label class="mb-1.5 block text-sm font-medium" :for="taskSelectId">Task</label>
          <select
            :id="taskSelectId"
            v-model="taskId"
            class="h-11 w-full rounded-xl border border-input bg-card px-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring">
            <option :value="null" disabled>Select a task</option>
            <option v-for="task in tasks" :key="task.id" :value="task.id">
              {{ task.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-medium" :for="subtaskSelectId">
            Subtask
          </label>
          <select
            :id="subtaskSelectId"
            v-model="subtaskId"
            :disabled="!subtaskOptions.length"
            class="h-11 w-full rounded-xl border border-input bg-card px-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50">
            <option :value="null" disabled>
              {{ taskId ? "Select a subtask" : "Pick a task first" }}
            </option>
            <option v-for="sub in subtaskOptions" :key="sub.id" :value="sub.id">
              {{ sub.name }}
            </option>
          </select>
        </div>
      </template>

      <div class="grid gap-4 sm:grid-cols-2">
        <UiInput v-model="startLocal" label="Start" type="datetime-local" />
        <UiInput v-model="endLocal" label="End" type="datetime-local" />
      </div>

      <UiAlert v-if="error" variant="danger">{{ error }}</UiAlert>
    </form>

    <template #footer>
      <UiButton variant="ghost" @click="open = false">Cancel</UiButton>
      <UiButton type="submit" form="entry-form" :loading="saving">
        {{ isEdit ? "Save" : "Add entry" }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, computed, watch, useId } from "vue";

  const props = defineProps({
    modelValue: { type: Boolean, default: false },
    entry: { type: Object, default: null },
    tasks: { type: Array, default: () => [] },
  });

  const emit = defineEmits(["update:modelValue", "saved"]);

  const { createTimeEntry, updateTimeEntry } = useTasks();
  const toast = useToast();

  const taskSelectId = useId();
  const subtaskSelectId = useId();

  const taskId = ref(null);
  const subtaskId = ref(null);
  const startLocal = ref("");
  const endLocal = ref("");
  const error = ref("");
  const saving = ref(false);

  const open = computed({
    get: () => props.modelValue,
    set: (val) => emit("update:modelValue", val),
  });

  const isEdit = computed(() => !!props.entry?.id);

  const subtaskOptions = computed(() => {
    const task = props.tasks.find((t) => t.id === taskId.value);
    return task ? task.subtasks : [];
  });

  // Reset the picked subtask when the task changes.
  watch(taskId, () => {
    if (!subtaskOptions.value.some((s) => s.id === subtaskId.value)) {
      subtaskId.value = null;
    }
  });

  watch(
    () => props.modelValue,
    (val) => {
      if (!val) return;
      error.value = "";
      if (props.entry) {
        taskId.value = props.entry.task_id;
        subtaskId.value = props.entry.subtask_id;
        startLocal.value = toDateTimeLocal(props.entry.clock_in);
        endLocal.value = props.entry.clock_out
          ? toDateTimeLocal(props.entry.clock_out)
          : toDateTimeLocal(new Date());
      } else {
        const now = new Date();
        const hourAgo = new Date(now.getTime() - 60 * 60 * 1000);
        taskId.value = null;
        subtaskId.value = null;
        startLocal.value = toDateTimeLocal(hourAgo);
        endLocal.value = toDateTimeLocal(now);
      }
    },
  );

  async function submit() {
    if (saving.value) return;
    error.value = "";

    if (!isEdit.value && !subtaskId.value) {
      error.value = "Pick a task and subtask.";
      return;
    }
    if (!startLocal.value || !endLocal.value) {
      error.value = "Both start and end are required.";
      return;
    }
    const start = fromDateTimeLocal(startLocal.value);
    const end = fromDateTimeLocal(endLocal.value);
    if (new Date(end) <= new Date(start)) {
      error.value = "The end must be after the start.";
      return;
    }

    saving.value = true;
    try {
      if (isEdit.value) {
        await updateTimeEntry(props.entry.id, start, end);
        toast.success("Time entry updated.");
      } else {
        await createTimeEntry(subtaskId.value, start, end);
        toast.success("Time entry added.");
      }
      emit("saved");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't save the time entry.";
      console.error("Error saving time entry:", err);
    } finally {
      saving.value = false;
    }
  }
</script>
