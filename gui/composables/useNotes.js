// Wraps the grouped-notes API calls so pages don't repeat the endpoint paths
// and request shapes. Must be called from a setup context.
export function useNotes() {
  const { $api } = useNuxtApp();

  return {
    getNotes: () => $api("/notes/user/get-notes/", { method: "GET" }),

    createGroup: (name, color = "") =>
      $api("/notes/user/create-group/", {
        method: "POST",
        body: { name, color },
      }),

    updateGroup: (id, payload) =>
      $api(`/notes/user/update-group/${id}/`, {
        method: "PATCH",
        body: payload,
      }),

    deleteGroup: (id) =>
      $api(`/notes/user/delete-group/${id}/`, { method: "DELETE" }),

    createNote: (groupId, title, body = "") =>
      $api("/notes/user/create-note/", {
        method: "POST",
        body: { group_id: groupId, title, body },
      }),

    updateNote: (id, payload) =>
      $api(`/notes/user/update-note/${id}/`, {
        method: "PATCH",
        body: payload,
      }),

    toggleNote: (id) =>
      $api(`/notes/user/toggle-note/${id}/`, { method: "POST" }),

    deleteNote: (id) =>
      $api(`/notes/user/delete-note/${id}/`, { method: "DELETE" }),
  };
}
