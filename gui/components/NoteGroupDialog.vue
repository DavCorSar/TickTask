<template>
  <UiModal v-model="open" :title="isEdit ? 'Edit group' : 'New group'">
    <form id="group-form" class="space-y-4" @submit.prevent="submit">
      <UiInput
        v-model="name"
        label="Name"
        placeholder="e.g. Shopping, Ideas, Bugs"
        icon="lucide:folder"
        autofocus />

      <div>
        <span class="mb-1.5 block text-sm font-medium">Color</span>
        <div class="flex gap-2">
          <button
            v-for="preset in NOTE_COLORS"
            :key="preset"
            type="button"
            class="size-7 rounded-full ring-offset-2 ring-offset-card transition"
            :class="color === preset ? 'ring-2 ring-foreground' : ''"
            :style="{ backgroundColor: preset }"
            @click="color = preset"></button>
        </div>
      </div>

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
      <UiButton type="submit" form="group-form" :loading="saving">
        {{ isEdit ? "Save" : "Create" }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, computed, watch } from "vue";

  const props = defineProps({
    modelValue: { type: Boolean, default: false },
    group: { type: Object, default: null },
  });

  const emit = defineEmits(["update:modelValue", "saved", "deleted"]);

  const { createGroup, updateGroup, deleteGroup } = useNotes();
  const toast = useToast();

  const name = ref("");
  const color = ref(NOTE_COLORS[0]);
  const error = ref("");
  const saving = ref(false);
  const deleting = ref(false);

  const open = computed({
    get: () => props.modelValue,
    set: (val) => emit("update:modelValue", val),
  });

  const isEdit = computed(() => !!props.group?.id);

  watch(
    () => props.modelValue,
    (val) => {
      if (!val) return;
      error.value = "";
      name.value = props.group?.name || "";
      color.value = props.group?.color || NOTE_COLORS[0];
    },
  );

  async function submit() {
    if (saving.value) return;
    error.value = "";

    if (!name.value.trim()) {
      error.value = "The name is required.";
      return;
    }

    saving.value = true;
    try {
      if (isEdit.value) {
        await updateGroup(props.group.id, {
          name: name.value.trim(),
          color: color.value,
        });
      } else {
        await createGroup(name.value.trim(), color.value);
      }
      toast.success(isEdit.value ? "Group updated." : "Group created.");
      emit("saved");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't save the group.";
      console.error("Error saving group:", err);
    } finally {
      saving.value = false;
    }
  }

  async function remove() {
    if (deleting.value) return;
    deleting.value = true;
    try {
      await deleteGroup(props.group.id);
      toast.success("Group deleted.");
      emit("deleted");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't delete the group.";
      console.error("Error deleting group:", err);
    } finally {
      deleting.value = false;
    }
  }
</script>
