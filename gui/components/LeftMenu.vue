<template>
  <v-navigation-drawer color="primary" expand-on-hover v-model:rail="rail">
    <v-img
      src="/logo_white.png"
      max-width="40"
      class="mx-auto my-5"
      title="TickTask" />

    <v-divider></v-divider>

    <v-list>
      <v-list-item
        prepend-icon="mdi-home"
        title="Home"
        value="home"
        to="/home"></v-list-item>

      <v-divider class="my-2"></v-divider>

      <v-list-item
        prepend-icon="mdi-clock-in"
        title="Time track"
        value="time-tracking"
        to="/time-tracking"></v-list-item>
      <v-list-item
        prepend-icon="mdi-history"
        title="Tracker history"
        value="time-history"
        to="/time-history"></v-list-item>
    </v-list>

    <template v-slot:append>
      <v-list>
        <v-list-item
          prepend-icon="mdi-logout"
          title="Salir"
          value="logout"
          @click="logout"
          v-if="auth.isAuthenticated.value"></v-list-item>
      </v-list>
    </template>
  </v-navigation-drawer>
</template>

<script setup>
  const auth = useAuth();
  const rail = ref(false);

  const logout = () => {
    auth.logout();
    navigateTo("/login");
  };
</script>
