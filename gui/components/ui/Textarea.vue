<template>
  <div class="w-full">
    <label
      v-if="label"
      :for="id"
      class="mb-1.5 block text-sm font-medium text-foreground">
      {{ label }}
    </label>
    <textarea
      :id="id"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      :class="[
        'w-full rounded-xl border bg-card px-3.5 py-2.5 text-foreground placeholder:text-muted-foreground transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent resize-y',
        error ? 'border-danger' : 'border-input',
      ]"
      @input="$emit('update:modelValue', $event.target.value)"></textarea>
    <p v-if="error" class="mt-1.5 text-sm text-danger">{{ error }}</p>
  </div>
</template>

<script setup>
  import { useId } from "vue";

  defineProps({
    modelValue: { type: String, default: "" },
    label: { type: String, default: "" },
    placeholder: { type: String, default: "" },
    rows: { type: [String, Number], default: 3 },
    error: { type: String, default: "" },
  });

  defineEmits(["update:modelValue"]);

  const id = useId();
</script>
