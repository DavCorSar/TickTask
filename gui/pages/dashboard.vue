<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Dashboard</h1>
      <p class="mt-1 text-muted-foreground">
        Hours spent across your tasks and subtasks.
      </p>
    </div>

    <UiCard>
      <div class="flex flex-col items-center gap-3 py-16 text-center">
        <div
          class="flex size-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <Icon name="lucide:chart-column" class="size-7" />
        </div>
        <div>
          <p class="font-semibold">Coming soon</p>
          <p class="mt-1 max-w-sm text-sm text-muted-foreground">
            Charts of time per task, trends over time, and summary stats will
            live here.
          </p>
        </div>
      </div>
    </UiCard>
  </div>
</template>

<script setup>
  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });
</script>
