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
        <h1 class="mt-4 text-2xl font-bold tracking-tight">
          Create your account
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Start tracking your time with TickTask
        </p>
      </div>

      <div class="card-surface p-6 shadow-card">
        <!-- Submitted: account is queued for approval -->
        <div
          v-if="submitted"
          class="flex flex-col items-center gap-3 py-4 text-center">
          <div
            class="flex size-12 items-center justify-center rounded-2xl bg-accent/15 text-accent">
            <Icon name="lucide:mail-check" class="size-6" />
          </div>
          <p class="font-medium">Request submitted</p>
          <p class="text-sm text-muted-foreground">{{ submitted }}</p>
          <UiButton to="/login" variant="ghost" size="sm" class="mt-2">
            Back to log in
          </UiButton>
        </div>

        <form v-else class="space-y-4" @submit.prevent="register">
          <UiInput
            v-model="username"
            label="Username"
            placeholder="choose a username"
            icon="lucide:user"
            autocomplete="username"
            autofocus />

          <UiInput
            v-model="password"
            label="Password"
            type="password"
            placeholder="••••••••"
            icon="lucide:lock"
            autocomplete="new-password"
            revealable />

          <UiInput
            v-model="confirmPassword"
            label="Confirm password"
            type="password"
            placeholder="••••••••"
            icon="lucide:lock"
            autocomplete="new-password"
            revealable
            @enter="register" />

          <UiAlert v-if="errorMessage" variant="danger">{{
            errorMessage
          }}</UiAlert>

          <UiButton type="submit" block size="lg" :loading="loading"
            >Sign up</UiButton
          >
        </form>
      </div>

      <p class="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?
        <NuxtLink
          to="/login"
          class="font-medium text-primary transition-colors hover:underline">
          Log in
        </NuxtLink>
      </p>

      <div class="mt-4 text-center">
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

  definePageMeta({ layout: "blank" });

  const auth = useAuth();

  const username = ref("");
  const password = ref("");
  const confirmPassword = ref("");
  const errorMessage = ref("");
  const submitted = ref("");
  const loading = ref(false);

  const register = async () => {
    if (loading.value) return;
    errorMessage.value = "";

    if (!username.value || !password.value) {
      errorMessage.value = "Please enter a username and password.";
      return;
    }
    if (password.value !== confirmPassword.value) {
      errorMessage.value = "The passwords don't match.";
      return;
    }

    loading.value = true;
    try {
      submitted.value = await auth.register(username.value, password.value);
    } catch (error) {
      errorMessage.value = error.message || "Couldn't create your account.";
    } finally {
      loading.value = false;
    }
  };
</script>
