<template>
  <div class="w-full">
    <label
      v-if="label"
      :for="id"
      class="mb-1.5 block text-sm font-medium text-foreground">
      {{ label }}
    </label>
    <div class="relative">
      <Icon
        v-if="icon"
        :name="icon"
        class="pointer-events-none absolute left-3 top-1/2 size-[18px] -translate-y-1/2 text-muted-foreground" />
      <input
        :id="id"
        :type="revealable && revealed ? 'text' : type"
        :value="modelValue"
        :placeholder="placeholder"
        :autofocus="autofocus"
        :autocomplete="autocomplete"
        :class="[
          'h-11 w-full rounded-xl border bg-card text-foreground placeholder:text-muted-foreground transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
          icon ? 'pl-10' : 'pl-3.5',
          revealable ? 'pr-10' : 'pr-3.5',
          error ? 'border-danger' : 'border-input',
        ]"
        @input="$emit('update:modelValue', $event.target.value)"
        @keyup.enter="$emit('enter')" />
      <button
        v-if="revealable"
        type="button"
        class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        @click="revealed = !revealed">
        <Icon
          :name="revealed ? 'lucide:eye' : 'lucide:eye-off'"
          class="size-[18px]" />
      </button>
    </div>
    <p v-if="error" class="mt-1.5 text-sm text-danger">{{ error }}</p>
  </div>
</template>

<script setup>
  import { ref, useId } from "vue";

  defineProps({
    modelValue: { type: [String, Number], default: "" },
    label: { type: String, default: "" },
    placeholder: { type: String, default: "" },
    type: { type: String, default: "text" },
    icon: { type: String, default: "" },
    error: { type: String, default: "" },
    autofocus: { type: Boolean, default: false },
    autocomplete: { type: String, default: "off" },
    revealable: { type: Boolean, default: false },
  });

  defineEmits(["update:modelValue", "enter"]);

  const id = useId();
  const revealed = ref(false);
</script>
