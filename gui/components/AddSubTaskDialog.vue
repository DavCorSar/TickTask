<template>
  <UiModal v-model="dialog" title="New subtask">
    <form id="add-subtask-form" class="space-y-4" @submit.prevent="submitForm">
      <UiInput
        v-model="subtaskName"
        label="Subtask name"
        placeholder="e.g. Design the homepage"
        icon="lucide:list-todo"
        :error="nameError"
        autofocus />

      <UiTextarea
        v-model="subtaskDescription"
        label="Description"
        placeholder="What does this subtask involve?"
        :rows="3"
        :error="descError" />
    </form>

    <template #footer>
      <UiButton variant="ghost" @click="dialog = false">Cancel</UiButton>
      <UiButton type="submit" form="add-subtask-form" :loading="loading"
        >Create subtask</UiButton
      >
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, watch } from "vue";

  const props = defineProps({
    modelValue: Boolean,
    taskId: Number,
  });

  const emit = defineEmits(["update:modelValue", "subtask-created"]);

  const { createSubtask } = useTasks();

  const dialog = ref(props.modelValue);
  const subtaskName = ref("");
  const subtaskDescription = ref("");
  const nameError = ref("");
  const descError = ref("");
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
    nameError.value = "";
    descError.value = "";

    if (!subtaskName.value.trim()) nameError.value = "The name is required.";
    if (!subtaskDescription.value.trim())
      descError.value = "The description is required.";
    if (nameError.value || descError.value) return;

    loading.value = true;
    try {
      const response = await createSubtask(
        props.taskId,
        subtaskName.value.trim(),
        subtaskDescription.value.trim(),
      );

      emit("subtask-created", response);
      dialog.value = false;
    } catch (err) {
      nameError.value =
        err?.data?.detail ||
        "Couldn't create the subtask. Does it already exist?";
      console.error("Error creating subtask:", err);
    } finally {
      loading.value = false;
    }
  }

  function resetForm() {
    subtaskName.value = "";
    subtaskDescription.value = "";
    nameError.value = "";
    descError.value = "";
  }
</script>
