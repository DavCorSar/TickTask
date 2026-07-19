<template>
  <UiModal v-model="open" :title="isEdit ? 'Edit note' : 'New note'">
    <form id="note-form" class="space-y-4" @submit.prevent="submit">
      <UiInput
        v-model="title"
        label="Title"
        placeholder="e.g. Buy milk"
        icon="lucide:sticky-note"
        autofocus />

      <UiTextarea
        v-model="body"
        label="Details"
        placeholder="Optional notes"
        :rows="3" />

      <UiAlert v-if="error" variant="danger">{{ error }}</UiAlert>
    </form>

    <template #footer>
      <UiButton
        v-if="isEdit"
        variant="ghost"
        icon="lucide:trash-2"
        class="mr-auto text-danger hover:bg-danger/10"
        :loading="deleting"
        @click="remove">
        Delete
      </UiButton>
      <UiButton variant="ghost" @click="open = false">Cancel</UiButton>
      <UiButton type="submit" form="note-form" :loading="saving">
        {{ isEdit ? "Save" : "Add" }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, computed, watch } from "vue";

  const props = defineProps({
    modelValue: { type: Boolean, default: false },
    note: { type: Object, default: null },
    groupId: { type: Number, default: null },
  });

  const emit = defineEmits(["update:modelValue", "saved", "deleted"]);

  const { createNote, updateNote, deleteNote } = useNotes();
  const toast = useToast();

  const title = ref("");
  const body = ref("");
  const error = ref("");
  const saving = ref(false);
  const deleting = ref(false);

  const open = computed({
    get: () => props.modelValue,
    set: (val) => emit("update:modelValue", val),
  });

  const isEdit = computed(() => !!props.note?.id);

  watch(
    () => props.modelValue,
    (val) => {
      if (!val) return;
      error.value = "";
      title.value = props.note?.title || "";
      body.value = props.note?.body || "";
    },
  );

  async function submit() {
    if (saving.value) return;
    error.value = "";

    if (!title.value.trim()) {
      error.value = "The title is required.";
      return;
    }

    saving.value = true;
    try {
      if (isEdit.value) {
        await updateNote(props.note.id, {
          title: title.value.trim(),
          body: body.value.trim(),
        });
      } else {
        await createNote(props.groupId, title.value.trim(), body.value.trim());
      }
      toast.success(isEdit.value ? "Note updated." : "Note added.");
      emit("saved");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't save the note.";
      console.error("Error saving note:", err);
    } finally {
      saving.value = false;
    }
  }

  async function remove() {
    if (deleting.value) return;
    deleting.value = true;
    try {
      await deleteNote(props.note.id);
      toast.success("Note deleted.");
      emit("deleted");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't delete the note.";
      console.error("Error deleting note:", err);
    } finally {
      deleting.value = false;
    }
  }
</script>
