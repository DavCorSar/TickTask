<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:items-end">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-card"
          :class="styles[toast.type].box"
          role="status">
          <Icon
            :name="styles[toast.type].icon"
            class="mt-0.5 size-[18px] shrink-0"
            :class="styles[toast.type].iconColor" />
          <p class="min-w-0 flex-1">{{ toast.message }}</p>
          <button
            class="-mr-1 shrink-0 rounded-md p-0.5 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Dismiss"
            @click="dismiss(toast.id)">
            <Icon name="lucide:x" class="size-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
  const { toasts, dismiss } = useToast();

  const styles = {
    success: {
      box: "border-accent/25 bg-card text-foreground",
      icon: "lucide:circle-check",
      iconColor: "text-accent",
    },
    error: {
      box: "border-danger/25 bg-card text-foreground",
      icon: "lucide:circle-alert",
      iconColor: "text-danger",
    },
    info: {
      box: "border-primary/25 bg-card text-foreground",
      icon: "lucide:info",
      iconColor: "text-primary",
    },
  };
</script>

<style scoped>
  .toast-enter-active,
  .toast-leave-active {
    transition: all 0.22s ease;
  }
  .toast-enter-from {
    opacity: 0;
    transform: translateY(8px);
  }
  .toast-leave-to {
    opacity: 0;
    transform: translateX(12px);
  }
</style>
