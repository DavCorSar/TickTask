export default defineNuxtRouteMiddleware(async (to, from) => {
  const { $api } = useNuxtApp();

  const auth = useAuth();

  const storedToken = localStorage.getItem("access_token");

  if (storedToken) {
    try {
      // Verify if token is still valid
      await $api("/auth/verify", {
        method: "POST",
        body: { token: storedToken },
      });

      // Permit continue to next page if token is valid
      auth.accessToken.value = storedToken;
      return;
    } catch (error) {
      console.warn("Invalid token. Closing session");
      auth.logout();
    }
  } else if (
    (!auth.isAuthenticated.value && to.meta.requiresAuth) ||
    (to.meta.requiresAuth && !storedToken)
  ) {
    auth.logout();
    return navigateTo("/login");
  }
});
