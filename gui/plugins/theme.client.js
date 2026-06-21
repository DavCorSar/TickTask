// Apply the persisted (or system-preferred) theme as early as possible on load.
export default defineNuxtPlugin(() => {
  const { init } = useTheme();
  init();
});
