<template>
    <v-container fluid class="fill-height">
        <Home />
    </v-container>
</template>

<script setup>

definePageMeta({
    middleware: 'auth',
    requiresAuth: true,
    layout: 'newdefault'
})
</script>