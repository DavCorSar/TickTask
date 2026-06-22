// Wraps the task / subtask / time-entry API calls so pages don't repeat the
// endpoint paths and request shapes. Must be called from a setup context.
export function useTasks() {
  const { $api } = useNuxtApp();

  return {
    fetchTasks: () =>
      $api("/ticktask/user/get-tasks-and-subtasks/", { method: "GET" }),

    createTask: (name) =>
      $api("/ticktask/user/create-task/", { method: "POST", body: { name } }),

    createSubtask: (taskId, name, description) =>
      $api("/ticktask/user/create-subtask/", {
        method: "POST",
        body: { task_id: taskId, name, description },
      }),

    deleteTask: (taskId) =>
      $api("/ticktask/user/delete-task/", {
        method: "POST",
        body: { task_id: taskId },
      }),

    deleteSubtask: (subtaskId) =>
      $api("/ticktask/user/delete-subtask/", {
        method: "POST",
        body: { subtask_id: subtaskId },
      }),

    restoreTask: (taskId) =>
      $api("/ticktask/user/restore-task/", {
        method: "POST",
        body: { task_id: taskId },
      }),

    restoreSubtask: (subtaskId) =>
      $api("/ticktask/user/restore-subtask/", {
        method: "POST",
        body: { subtask_id: subtaskId },
      }),

    clockIn: (subtaskId) =>
      $api("/ticktask/user/clock-in/", {
        method: "POST",
        body: { subtask_id: subtaskId },
      }),

    clockOut: (entityId) =>
      $api("/ticktask/user/clock-out/", {
        method: "POST",
        body: { entity_id: entityId },
      }),

    getClockedIn: () =>
      $api("/ticktask/user/get-clocked-in-time-entry/", { method: "GET" }),

    getTimeEntries: (subtaskId, lastHours) =>
      $api("/ticktask/user/get-time-entries/", {
        method: "POST",
        body: { subtask_id: subtaskId, last_hours: lastHours },
      }),

    getTimeHistory: (start, end, includeDeleted = false) =>
      $api("/ticktask/user/get-time-history/", {
        method: "GET",
        query: { start, end, include_deleted: includeDeleted },
      }),

    createTimeEntry: (subtaskId, clockIn, clockOut) =>
      $api("/ticktask/user/create-time-entry/", {
        method: "POST",
        body: { subtask_id: subtaskId, clock_in: clockIn, clock_out: clockOut },
      }),

    updateTimeEntry: (entityId, clockIn, clockOut) =>
      $api("/ticktask/user/update-time-entry/", {
        method: "POST",
        body: { entity_id: entityId, clock_in: clockIn, clock_out: clockOut },
      }),
  };
}
