// Light/dark theme management. Persists choice in localStorage and toggles the
// `dark` class on <html>, which flips the CSS variables defined in tailwind.css.
export const useTheme = () => {
  const theme = useState("theme", () => "light");

  const apply = (value) => {
    if (!import.meta.client) return;
    document.documentElement.classList.toggle("dark", value === "dark");
    localStorage.setItem("theme", value);
  };

  const setTheme = (value) => {
    theme.value = value;
    apply(value);
  };

  const toggle = () => setTheme(theme.value === "dark" ? "light" : "dark");

  const init = () => {
    if (!import.meta.client) return;
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)",
    ).matches;
    setTheme(stored || (prefersDark ? "dark" : "light"));
  };

  return { theme, setTheme, toggle, init };
};
