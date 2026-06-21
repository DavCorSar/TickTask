<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Calendar</h1>
      <p class="mt-1 text-muted-foreground">
        Review tracked time and plan future events.
      </p>
    </div>

    <UiCard>
      <div class="flex flex-col items-center gap-3 py-16 text-center">
        <div
          class="flex size-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <Icon name="lucide:calendar-days" class="size-7" />
        </div>
        <div>
          <p class="font-semibold">Coming soon</p>
          <p class="mt-1 max-w-sm text-sm text-muted-foreground">
            A month/week calendar showing your tracked time plus the events you
            schedule.
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
