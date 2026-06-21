<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <!-- Decorative gradient -->
    <div
      class="pointer-events-none absolute inset-x-0 top-0 -z-10 flex justify-center blur-3xl"
      aria-hidden="true">
      <div
        class="h-64 w-[32rem] bg-gradient-to-tr from-primary/25 to-accent/15 opacity-70"></div>
    </div>

    <div class="absolute right-4 top-4">
      <UiThemeToggle />
    </div>

    <div class="w-full max-w-sm">
      <div class="mb-8 flex flex-col items-center text-center">
        <div
          class="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-soft">
          <Icon name="lucide:timer" class="size-6" />
        </div>
        <h1 class="mt-4 text-2xl font-bold tracking-tight">Welcome back</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Log in to your TickTask account
        </p>
      </div>

      <div class="card-surface p-6 shadow-card">
        <form class="space-y-4" @submit.prevent="login">
          <UiInput
            v-model="username"
            label="Username"
            placeholder="your username"
            icon="lucide:user"
            autocomplete="username"
            autofocus />

          <UiInput
            v-model="password"
            label="Password"
            type="password"
            placeholder="••••••••"
            icon="lucide:lock"
            autocomplete="current-password"
            revealable
            @enter="login" />

          <UiAlert v-if="errorMessage" variant="danger">{{
            errorMessage
          }}</UiAlert>

          <UiButton type="submit" block size="lg" :loading="loading"
            >Log in</UiButton
          >
        </form>
      </div>

      <div class="mt-6 text-center">
        <NuxtLink
          to="/"
          class="text-sm text-muted-foreground transition-colors hover:text-foreground">
          ← Back to home
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { ref } from "vue";
  import { useRouter } from "vue-router";

  definePageMeta({ layout: "blank" });

  const auth = useAuth();
  const router = useRouter();

  const username = ref("");
  const password = ref("");
  const errorMessage = ref("");
  const loading = ref(false);

  const login = async () => {
    if (loading.value) return;
    errorMessage.value = "";

    if (!username.value || !password.value) {
      errorMessage.value = "Please enter your username and password.";
      return;
    }

    loading.value = true;
    try {
      const success = await auth.login(username.value, password.value);
      if (success) router.push("/home");
    } catch (error) {
      errorMessage.value = error.message || "Incorrect username or password.";
    } finally {
      loading.value = false;
    }
  };
</script>
