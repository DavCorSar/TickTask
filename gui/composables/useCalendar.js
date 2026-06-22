// Wraps the calendar / event API calls. Must be called from a setup context.
export function useCalendar() {
  const { $api } = useNuxtApp();

  return {
    getCalendar: (start, end, includeDeleted = false) =>
      $api("/calendar/user/get-calendar/", {
        method: "GET",
        query: { start, end, include_deleted: includeDeleted },
      }),

    createEvent: (payload) =>
      $api("/calendar/user/create-event/", { method: "POST", body: payload }),

    updateEvent: (id, payload) =>
      $api(`/calendar/user/update-event/${id}/`, {
        method: "PATCH",
        body: payload,
      }),

    deleteEvent: (id) =>
      $api(`/calendar/user/delete-event/${id}/`, { method: "DELETE" }),
  };
}
