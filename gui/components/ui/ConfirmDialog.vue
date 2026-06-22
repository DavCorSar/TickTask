<template>
  <UiModal
    :model-value="modelValue"
    :title="title"
    max-width="26rem"
    @update:model-value="emit('update:modelValue', $event)">
    <p class="text-sm text-muted-foreground">{{ message }}</p>

    <template #footer>
      <UiButton variant="ghost" @click="emit('update:modelValue', false)">
        {{ cancelLabel }}
      </UiButton>
      <UiButton :variant="variant" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </UiButton>
    </template>
  </UiModal>
</template>

<script setup>
  defineProps({
    modelValue: { type: Boolean, default: false },
    title: { type: String, default: "Are you sure?" },
    message: { type: String, default: "" },
    confirmLabel: { type: String, default: "Confirm" },
    cancelLabel: { type: String, default: "Cancel" },
    variant: { type: String, default: "danger" },
    loading: { type: Boolean, default: false },
  });

  const emit = defineEmits(["update:modelValue", "confirm"]);
</script>
