import { jwtDecode } from "jwt-decode";

export const useAuth = () => {
  const { $api } = useNuxtApp();

  const accessToken = useState("access_token", () => null);
  const refreshToken = useState("refresh_token", () => null);
  const user = useState("user", () => null);

  const setSession = (response) => {
    if (!response.access || !response.refresh) {
      throw new Error("Tokens were not received successfully");
    }

    accessToken.value = response.access;
    refreshToken.value = response.refresh;
    user.value = jwtDecode(response.access);

    localStorage.setItem("access_token", accessToken.value);
    localStorage.setItem("refresh_token", refreshToken.value);

    scheduleTokenRefresh();
  };

  const login = async (username, password) => {
    try {
      logout();

      const response = await $api("/auth/login", {
        method: "POST",
        body: { username, password },
      });

      setSession(response);
      return true;
    } catch (error) {
      // 403 = account exists but gated (pending/rejected): show the server's
      // reason. Anything else stays a generic credentials message.
      throw new Error(error?.data?.detail || "Invalid user or password");
    }
  };

  // Registration is gated: it does not sign the user in, it queues the account
  // for admin approval and returns the server's status message.
  const register = async (username, password) => {
    try {
      const response = await $api("/auth/register", {
        method: "POST",
        body: { username, password },
      });
      return response.message || "Your request has been submitted.";
    } catch (error) {
      // Surface the server's reason (username taken, password too weak, …).
      throw new Error(error?.data?.detail || "Couldn't create your account.");
    }
  };

  const refresh = async () => {
    if (!refreshToken.value) return;
    try {
      const response = await $api("/auth/refresh", {
        method: "POST",
        body: { refresh: refreshToken.value },
      });
      accessToken.value = response.access;
      user.value = jwtDecode(response.access);

      scheduleTokenRefresh();
    } catch (error) {
      console.log("Error refreshing token:", error);
      logout();
    }
  };

  const logout = () => {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  };

  const isAuthenticated = computed(() => !!accessToken.value);

  const scheduleTokenRefresh = () => {
    if (!accessToken.value) return;

    const decoded = jwtDecode(accessToken.value);
    const now = Math.floor(Date.now() / 1000);
    const timeLeft = decoded.exp - now;

    // Refrescar 30 segundos antes de que expire el token
    setTimeout(
      async () => {
        refresh();
      },
      (timeLeft - 30) * 1000,
    );
  };

  return {
    accessToken,
    refreshToken,
    user,
    login,
    register,
    refresh,
    logout,
    isAuthenticated,
  };
};
