import { useRuntimeConfig } from "#app";

export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig();

  const accessToken = useState("access_token");
  const auth = useAuth();

  const api = $fetch.create({
    baseURL: config.public.apiBaseUrl,
    headers: {
      "Content-Type": "application/json",
    },
    onRequest({ request, options, error }) {
      if (accessToken.value) {
        options.headers.set("Authorization", `Bearer ${accessToken.value}`);
      }
    },
    async onResponseError({ response }) {
      if (response.status === 401) {
        auth.logout();
        await nuxtApp.runWithContext(() => navigateTo("/login"));
      }
    },
  });

  // Expose to useNuxtApp().$api
  return {
    provide: {
      api,
    },
  };
});
