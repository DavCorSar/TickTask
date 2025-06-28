<template>
  <v-container fluid>
    <span class="mt-2 text-lg font-semibold text-gray-800"
      >TODO: Define the page that will contain the time-tracker</span
    >
  </v-container>
</template>

<script setup>
  definePageMeta({
    middleware: "auth",
    requiresAuth: true,
    layout: "defaultlogged",
  });
</script>
