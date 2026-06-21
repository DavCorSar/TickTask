<template>
  <div class="card-surface" :class="padded ? 'p-6' : ''">
    <div
      v-if="$slots.header || title"
      class="mb-4 flex items-start justify-between gap-4">
      <div>
        <h3 v-if="title" class="text-base font-semibold tracking-tight">
          {{ title }}
        </h3>
        <p v-if="subtitle" class="mt-0.5 text-sm text-muted-foreground">
          {{ subtitle }}
        </p>
        <slot name="header" />
      </div>
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<script setup>
  defineProps({
    title: { type: String, default: "" },
    subtitle: { type: String, default: "" },
    padded: { type: Boolean, default: true },
  });
</script>
