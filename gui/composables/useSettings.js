// Wraps the per-user settings API (currently Telegram reminders).
// Must be called from a setup context.
export function useSettings() {
  const { $api } = useNuxtApp();

  return {
    getTelegram: () => $api("/telegram/settings/", { method: "GET" }),

    updateTelegram: (enabled, reminderLeadMinutes, timezone = "") =>
      $api("/telegram/settings/", {
        method: "POST",
        body: {
          enabled,
          reminder_lead_minutes: reminderLeadMinutes,
          timezone,
        },
      }),

    linkTelegram: () => $api("/telegram/link/", { method: "POST" }),

    unlinkTelegram: () => $api("/telegram/unlink/", { method: "POST" }),

    testTelegram: () => $api("/telegram/test/", { method: "POST" }),
  };
}
