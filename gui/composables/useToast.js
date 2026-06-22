// A tiny global toast/notification store. Module-level state makes it a
// singleton shared across the app, so any component can push a notification.
import { reactive } from "vue";

const toasts = reactive([]);
let nextId = 0;

function show(message, type, timeout) {
  const id = ++nextId;
  toasts.push({ id, message, type });
  if (timeout) setTimeout(() => dismiss(id), timeout);
  return id;
}

function dismiss(id) {
  const index = toasts.findIndex((t) => t.id === id);
  if (index !== -1) toasts.splice(index, 1);
}

export function useToast() {
  return {
    toasts,
    dismiss,
    success: (message, timeout = 4000) => show(message, "success", timeout),
    error: (message, timeout = 6000) => show(message, "error", timeout),
    info: (message, timeout = 4000) => show(message, "info", timeout),
  };
}
