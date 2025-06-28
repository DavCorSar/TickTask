export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuth();

  if (!auth.isAuthenticated.value && to.meta.requiresAuth) {
    return navigateTo("/login");
  }
});
