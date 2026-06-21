<template>
  <header
    class="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
      <NuxtLink to="/" class="flex items-center gap-2.5">
        <div
          class="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft">
          <Icon name="lucide:timer" class="size-5" />
        </div>
        <span class="text-lg font-bold tracking-tight">TickTask</span>
      </NuxtLink>

      <div class="ml-auto flex items-center gap-1.5">
        <UiThemeToggle />
        <UiButton
          v-if="auth.isAuthenticated.value"
          to="/home"
          variant="secondary"
          size="sm"
          icon="lucide:layout-dashboard">
          Open app
        </UiButton>
        <UiButton
          v-else
          to="/login"
          variant="primary"
          size="sm"
          icon="lucide:log-in">
          Log in
        </UiButton>
      </div>
    </div>
  </header>
</template>

<script setup>
  const auth = useAuth();
</script>
