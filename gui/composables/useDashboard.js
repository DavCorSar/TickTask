// Wraps the dashboard aggregation API calls. Must be called from a setup context.
export function useDashboard() {
  const { $api } = useNuxtApp();

  return {
    getSummary: (includeDeleted = false) =>
      $api("/dashboard/user/get-summary/", {
        method: "GET",
        query: { include_deleted: includeDeleted },
      }),

    getTimeSeries: (start, end, bucket, includeDeleted = false) =>
      $api("/dashboard/user/get-time-series/", {
        method: "GET",
        query: { start, end, bucket, include_deleted: includeDeleted },
      }),
  };
}
