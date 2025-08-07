<template>
  <v-app-bar app color="primary">
    <v-img
      src="/logo_white.png"
      max-width="40"
      class="mx-6 my-5"
      title="TickTask" />
    <v-app-bar-title>Tick-Task</v-app-bar-title>
    <template v-slot:append>
      <v-btn text to="/" prepend-icon="mdi-home-variant">Inicio</v-btn>
      <v-btn
        text
        to="/login"
        v-if="!auth.isAuthenticated.value"
        class="ml-2"
        prepend-icon="mdi-login"
        >Login</v-btn
      >
      <v-btn
        text
        @click="logout()"
        v-if="auth.isAuthenticated.value"
        prepend-icon="mdi-logout"
        class="ml-2"
        >Logout</v-btn
      >
    </template>
  </v-app-bar>
</template>

<script setup>
  const auth = useAuth();

  const logout = () => {
    auth.logout();
    navigateTo("/login");
  };
</script>
