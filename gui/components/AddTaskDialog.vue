<template>
  <UiModal v-model="dialog" title="New task">
    <form id="add-task-form" class="space-y-4" @submit.prevent="submitForm">
      <UiInput
        v-model="taskName"
        label="Task name"
        placeholder="e.g. Website redesign"
        icon="lucide:folder"
        :error="error"
        autofocus
        @enter="submitForm" />
    </form>

    <template #footer>
      <UiButton variant="ghost" @click="dialog = false">Cancel</UiButton>
      <UiButton type="submit" form="add-task-form" :loading="loading"
        >Create task</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, watch } from "vue";

  const props = defineProps({
    modelValue: Boolean,
  });

  const emit = defineEmits(["update:modelValue", "task-created"]);

  const { $api } = useNuxtApp();

  const dialog = ref(props.modelValue);
  const taskName = ref("");
  const error = ref("");
  const loading = ref(false);

  watch(
    () => props.modelValue,
    (val) => {
      dialog.value = val;
      if (val) resetForm();
    },
  );

  watch(dialog, (val) => emit("update:modelValue", val));

  async function submitForm() {
    if (loading.value) return;
    error.value = "";

    if (!taskName.value.trim()) {
      error.value = "The name is required.";
      return;
    }

    loading.value = true;
    try {
      const response = await $api("/ticktask/user/create-task/", {
        method: "POST",
        body: { name: taskName.value.trim() },
      });

      emit("task-created", response);
      dialog.value = false;
    } catch (err) {
      error.value =
        err?.data?.detail || "Couldn't create the task. Does it already exist?";
      console.error("Error creating task:", err);
    } finally {
      loading.value = false;
    }
  }

  function resetForm() {
    taskName.value = "";
    error.value = "";
  }
</script>
