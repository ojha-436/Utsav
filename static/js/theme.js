// Light/dark theme toggle. Loaded in <head> (not as a module) so the saved or
// system theme is applied before the first paint, with no flash of the wrong colours.
(() => {
  const STORAGE_KEY = "utsav-theme";
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  // Storage can be unavailable (private mode, blocked site data); the toggle still works per page.
  const savedTheme = () => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  };
  const saveTheme = (theme) => {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* not persisted; fine */
    }
  };
  const preferredTheme = () => savedTheme() || (systemDark.matches ? "dark" : "light");

  function applyTheme(theme) {
    root.dataset.theme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(theme === "dark"));
    });
  }

  applyTheme(preferredTheme());
  // Follow the device setting until the user picks a theme themselves.
  systemDark.addEventListener("change", () => {
    if (!savedTheme()) applyTheme(preferredTheme());
  });
  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(root.dataset.theme);
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.dataset.theme === "dark" ? "light" : "dark";
        saveTheme(next);
        applyTheme(next);
      });
    });
  });
})();
