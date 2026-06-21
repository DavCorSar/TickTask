<template>
  <Home />
</template>

<script setup>
  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });
</script>
