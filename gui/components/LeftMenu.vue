<template>
  <!-- Mobile backdrop -->
  <Transition name="fade">
    <div
      v-if="open"
      class="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden"
      @click="emit('close')"></div>
  </Transition>

  <aside
    :class="[
      'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-card transition-transform duration-200 lg:static lg:translate-x-0',
      open ? 'translate-x-0' : '-translate-x-full',
    ]">
    <!-- Brand -->
    <div class="flex h-16 items-center gap-2.5 px-4">
      <div
        class="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft">
        <Icon name="lucide:timer" class="size-5" />
      </div>
      <span class="text-lg font-bold tracking-tight">TickTask</span>
      <div class="ml-auto">
        <UiThemeToggle />
      </div>
    </div>

    <!-- Nav -->
    <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
      <NuxtLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors"
        :class="
          isActive(item.to)
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        "
        @click="emit('navigate')">
        <Icon :name="item.icon" class="size-[18px]" />
        {{ item.label }}
      </NuxtLink>
    </nav>

    <!-- Account -->
    <div class="border-t border-border p-3">
      <div class="flex items-center gap-3 rounded-xl px-3 py-2">
        <div
          class="flex size-9 items-center justify-center rounded-full bg-muted text-sm font-semibold text-muted-foreground">
          {{ initials }}
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium">{{ displayName }}</p>
          <p class="truncate text-xs text-muted-foreground">Signed in</p>
        </div>
        <button
          class="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger"
          title="Log out"
          @click="logout">
          <Icon name="lucide:log-out" class="size-[18px]" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
  import { computed } from "vue";

  defineProps({
    open: { type: Boolean, default: false },
  });

  const emit = defineEmits(["close", "navigate"]);

  const auth = useAuth();
  const route = useRoute();

  const items = [
    { label: "Overview", to: "/home", icon: "lucide:layout-dashboard" },
    { label: "Time tracking", to: "/time-tracking", icon: "lucide:timer" },
    { label: "Dashboard", to: "/dashboard", icon: "lucide:chart-column" },
    { label: "Calendar", to: "/calendar", icon: "lucide:calendar-days" },
    { label: "History", to: "/time-history", icon: "lucide:history" },
    { label: "Settings", to: "/settings", icon: "lucide:settings" },
  ];

  const isActive = (to) => route.path === to;

  const displayName = computed(
    () => auth.user.value?.username || auth.user.value?.name || "My account",
  );

  const initials = computed(() => displayName.value.slice(0, 2).toUpperCase());

  const logout = () => {
    auth.logout();
    navigateTo("/login");
  };
</script>

<style scoped>
  .fade-enter-active,
  .fade-leave-active {
    transition: opacity 0.2s ease;
  }
  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
  }
</style>
