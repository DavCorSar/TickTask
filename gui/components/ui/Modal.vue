<template>
  <Teleport to="body">
    <Transition name="overlay">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @keydown.esc="close">
        <div
          class="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
          @click="close"></div>

        <div
          class="relative w-full animate-scale-in card-surface shadow-card"
          :style="{ maxWidth }"
          role="dialog"
          aria-modal="true">
          <div
            class="flex items-center justify-between border-b border-border px-6 py-4">
            <h3 class="text-base font-semibold tracking-tight">{{ title }}</h3>
            <button
              class="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              @click="close">
              <Icon name="lucide:x" class="size-5" />
            </button>
          </div>

          <div class="px-6 py-5">
            <slot />
          </div>

          <div
            v-if="$slots.footer"
            class="flex justify-end gap-2 border-t border-border px-6 py-4">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
  const props = defineProps({
    modelValue: { type: Boolean, default: false },
    title: { type: String, default: "" },
    maxWidth: { type: String, default: "32rem" },
  });

  const emit = defineEmits(["update:modelValue"]);

  const close = () => emit("update:modelValue", false);
</script>

<style scoped>
  .overlay-enter-active,
  .overlay-leave-active {
    transition: opacity 0.18s ease;
  }
  .overlay-enter-from,
  .overlay-leave-to {
    opacity: 0;
  }
</style>
