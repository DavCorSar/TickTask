<template>
  <div class="mx-auto max-w-6xl space-y-8">
    <!-- Greeting -->
    <div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">
        {{ greeting }}
      </h1>
      <p class="mt-1 text-muted-foreground">
        Here's your TickTask workspace. What's next?
      </p>
    </div>

    <!-- Quick actions -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <NuxtLink
        v-for="action in actions"
        :key="action.to"
        :to="action.to"
        class="card-surface group flex flex-col gap-3 p-5 transition-all hover:-translate-y-0.5 hover:shadow-card">
        <div
          class="flex size-11 items-center justify-center rounded-xl transition-colors"
          :class="action.tint">
          <Icon :name="action.icon" class="size-5" />
        </div>
        <div>
          <h3 class="font-semibold">{{ action.title }}</h3>
          <p class="mt-0.5 text-sm text-muted-foreground">{{ action.text }}</p>
        </div>
        <span
          class="mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
          Open <Icon name="lucide:arrow-right" class="size-4" />
        </span>
      </NuxtLink>
    </div>

    <!-- Placeholder for upcoming overview widgets -->
    <UiCard
      title="At a glance"
      subtitle="Summary widgets will appear here as the dashboard takes shape.">
      <div
        class="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted-foreground">
        <Icon name="lucide:sparkles" class="size-8" />
        <p class="text-sm">
          Your time stats and upcoming events will show up here.
        </p>
      </div>
    </UiCard>
  </div>
</template>

<script setup>
  import { computed } from "vue";

  const greeting = computed(() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  });

  const actions = [
    {
      title: "Time tracking",
      text: "Clock in and out of your tasks.",
      to: "/time-tracking",
      icon: "lucide:timer",
      tint: "bg-primary/10 text-primary",
    },
    {
      title: "Dashboard",
      text: "See hours spent per task.",
      to: "/dashboard",
      icon: "lucide:chart-column",
      tint: "bg-accent/10 text-accent",
    },
    {
      title: "Calendar",
      text: "Plan and review your agenda.",
      to: "/calendar",
      icon: "lucide:calendar-days",
      tint: "bg-primary/10 text-primary",
    },
    {
      title: "History",
      text: "Browse past time entries.",
      to: "/time-history",
      icon: "lucide:history",
      tint: "bg-muted text-muted-foreground",
    },
  ];
</script>
