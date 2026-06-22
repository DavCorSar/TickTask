<template>
  <UiCard>
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="truncate text-sm font-medium text-muted-foreground">
          {{ label }}
        </p>
        <p class="mt-1 text-2xl font-bold tracking-tight">{{ value }}</p>
        <p v-if="hint" class="mt-0.5 truncate text-xs text-muted-foreground">
          {{ hint }}
        </p>
      </div>
      <div
        v-if="icon"
        class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <Icon :name="icon" class="size-5" />
      </div>
    </div>
  </UiCard>
</template>

<script setup>
  defineProps({
    label: { type: String, required: true },
    value: { type: [String, Number], default: "—" },
    hint: { type: String, default: "" },
    icon: { type: String, default: "" },
  });
</script>
