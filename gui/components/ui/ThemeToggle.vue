<template>
  <button
    class="inline-flex size-10 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggle">
    <Icon
      :name="theme === 'dark' ? 'lucide:sun' : 'lucide:moon'"
      class="size-5" />
  </button>
</template>

<script setup>
  const { theme, toggle } = useTheme();
</script>
