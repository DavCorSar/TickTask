<template>
  <v-container class="mx-auto">
    <v-row justify="center" align="center" class="text-center" no-gutters>
      <v-col cols="12" md="4">
        <v-btn
          @click="goTo('time-tracking')"
          variant="text"
          size="200"
          stacked
          color="primary">
          <v-icon size="150">mdi-clock-in</v-icon>
          <span class="mt-2 text-lg font-semibold text-gray-800"
            >Time track</span
          >
        </v-btn>
      </v-col>

      <v-col cols="12" md="4">
        <v-btn
          @click="goTo('time-history')"
          variant="text"
          size="200"
          stacked
          color="primary">
          <v-icon size="150">mdi-history</v-icon>
          <span class="mt-2 text-lg font-semibold text-gray-800"
            >Tracker history</span
          >
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  const router = useRouter();

  function goTo(path) {
    router.push(`/${path}`);
  }
</script>
