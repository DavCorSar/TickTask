<template>
  <UiModal v-model="open" :title="isEdit ? 'Edit event' : 'New event'">
    <form id="event-form" class="space-y-4" @submit.prevent="submit">
      <UiInput
        v-model="title"
        label="Title"
        placeholder="e.g. Team meeting"
        icon="lucide:calendar-days"
        autofocus />

      <UiTextarea
        v-model="description"
        label="Description"
        placeholder="Optional details"
        :rows="2" />

      <div class="grid gap-4 sm:grid-cols-2">
        <UiInput v-model="startLocal" label="Start" type="datetime-local" />
        <UiInput
          v-model="endLocal"
          label="End (optional)"
          type="datetime-local" />
      </div>

      <label
        class="flex w-fit cursor-pointer items-center gap-2 text-sm font-medium">
        <input
          v-model="allDay"
          type="checkbox"
          class="size-4 rounded border-input text-primary focus:ring-2 focus:ring-ring" />
        All day
      </label>

      <div>
        <span class="mb-1.5 block text-sm font-medium">Color</span>
        <div class="flex gap-2">
          <button
            v-for="preset in presets"
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
      <UiButton type="submit" form="event-form" :loading="saving">
        {{ isEdit ? "Save" : "Create" }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
  import { ref, computed, watch } from "vue";

  const props = defineProps({
    modelValue: { type: Boolean, default: false },
    event: { type: Object, default: null },
    defaultStart: { type: String, default: null },
  });

  const emit = defineEmits(["update:modelValue", "saved", "deleted"]);

  const { createEvent, updateEvent, deleteEvent } = useCalendar();
  const toast = useToast();

  const presets = [
    "#007CBF",
    "#5EA611",
    "#D30F4B",
    "#F59E0B",
    "#7C3AED",
    "#0EA5E9",
  ];

  const title = ref("");
  const description = ref("");
  const allDay = ref(false);
  const startLocal = ref("");
  const endLocal = ref("");
  const color = ref(presets[0]);
  const error = ref("");
  const saving = ref(false);
  const deleting = ref(false);

  const open = computed({
    get: () => props.modelValue,
    set: (val) => emit("update:modelValue", val),
  });

  const isEdit = computed(() => !!props.event?.id);

  watch(
    () => props.modelValue,
    (val) => {
      if (!val) return;
      error.value = "";
      if (props.event) {
        title.value = props.event.title;
        description.value = props.event.description || "";
        allDay.value = props.event.all_day;
        startLocal.value = toDateTimeLocal(props.event.start);
        endLocal.value = props.event.end
          ? toDateTimeLocal(props.event.end)
          : "";
        color.value = props.event.color || presets[0];
      } else {
        const base = props.defaultStart
          ? new Date(props.defaultStart)
          : new Date();
        title.value = "";
        description.value = "";
        allDay.value = false;
        startLocal.value = toDateTimeLocal(base);
        endLocal.value = "";
        color.value = presets[0];
      }
    },
  );

  async function submit() {
    if (saving.value) return;
    error.value = "";

    if (!title.value.trim()) {
      error.value = "The title is required.";
      return;
    }
    if (!startLocal.value) {
      error.value = "The start is required.";
      return;
    }

    const payload = {
      title: title.value.trim(),
      description: description.value.trim(),
      all_day: allDay.value,
      start: fromDateTimeLocal(startLocal.value),
      end: endLocal.value ? fromDateTimeLocal(endLocal.value) : null,
      color: color.value,
    };

    if (payload.end && new Date(payload.end) < new Date(payload.start)) {
      error.value = "The end can't be before the start.";
      return;
    }

    saving.value = true;
    try {
      if (isEdit.value) {
        await updateEvent(props.event.id, payload);
      } else {
        await createEvent(payload);
      }
      toast.success(isEdit.value ? "Event updated." : "Event created.");
      emit("saved");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't save the event.";
      console.error("Error saving event:", err);
    } finally {
      saving.value = false;
    }
  }

  async function remove() {
    if (deleting.value) return;
    deleting.value = true;
    try {
      await deleteEvent(props.event.id);
      toast.success("Event deleted.");
      emit("deleted");
      open.value = false;
    } catch (err) {
      error.value = err?.data?.detail || "Couldn't delete the event.";
      console.error("Error deleting event:", err);
    } finally {
      deleting.value = false;
    }
  }
</script>
