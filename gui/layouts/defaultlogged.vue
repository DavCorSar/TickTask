<template>
  <div class="flex min-h-screen bg-background">
    <LeftMenu
      :open="sidebarOpen"
      @close="sidebarOpen = false"
      @navigate="sidebarOpen = false" />

    <div class="flex min-w-0 flex-1 flex-col">
      <!-- Mobile top bar -->
      <header
        class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur lg:hidden">
        <button
          class="inline-flex size-10 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          @click="sidebarOpen = true">
          <Icon name="lucide:menu" class="size-5" />
        </button>
        <span class="text-base font-bold tracking-tight">TickTask</span>
        <div class="ml-auto">
          <UiThemeToggle />
        </div>
      </header>

      <main class="flex-1 p-4 sm:p-6 lg:p-8">
        <slot />
      </main>
    </div>

    <UiToastContainer />
  </div>
</template>

<script setup>
  import { ref } from "vue";

  const sidebarOpen = ref(false);
</script>
