<template>
  <section class="relative overflow-hidden">
    <!-- Decorative gradient -->
    <div
      class="pointer-events-none absolute inset-x-0 -top-40 -z-10 flex justify-center blur-3xl"
      aria-hidden="true">
      <div
        class="h-72 w-[36rem] bg-gradient-to-tr from-primary/30 to-accent/20 opacity-60"></div>
    </div>

    <div
      class="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center sm:py-32">
      <span
        class="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-1.5 text-sm text-muted-foreground">
        <span class="size-2 rounded-full bg-accent"></span>
        Track time. Plan ahead. Stay on top.
      </span>

      <h1 class="text-4xl font-extrabold tracking-tight sm:text-6xl">
        Your tasks and time,
        <span
          class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          in one place
        </span>
      </h1>

      <p class="mt-6 max-w-xl text-lg text-muted-foreground">
        Organize work into tasks and subtasks, clock in and out as you go, and
        see exactly where your hours went — with a dashboard and calendar to
        plan what's next.
      </p>

      <div class="mt-10 flex flex-wrap items-center justify-center gap-3">
        <UiButton
          :to="auth.isAuthenticated.value ? '/home' : '/signup'"
          size="lg"
          icon="lucide:arrow-right">
          {{ auth.isAuthenticated.value ? "Open the app" : "Get started" }}
        </UiButton>
        <UiButton
          v-if="!auth.isAuthenticated.value"
          to="/login"
          variant="ghost"
          size="lg">
          Log in
        </UiButton>
      </div>

      <div class="mt-16 grid w-full gap-4 sm:grid-cols-3">
        <div
          v-for="f in features"
          :key="f.title"
          class="card-surface p-5 text-left">
          <div
            class="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Icon :name="f.icon" class="size-5" />
          </div>
          <h3 class="mt-4 font-semibold">{{ f.title }}</h3>
          <p class="mt-1 text-sm text-muted-foreground">{{ f.text }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
  const auth = useAuth();

  const features = [
    {
      icon: "lucide:list-checks",
      title: "Tasks & subtasks",
      text: "Break work down and keep everything structured.",
    },
    {
      icon: "lucide:timer",
      title: "Time tracking",
      text: "One-tap clock in / out on whatever you're doing.",
    },
    {
      icon: "lucide:calendar-days",
      title: "Plan ahead",
      text: "A calendar and dashboard to review and schedule.",
    },
  ];
</script>
