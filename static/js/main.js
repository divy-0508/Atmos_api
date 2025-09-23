// main.js — theme toggle and persistence
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("theme-toggle");
  const saved = localStorage.getItem("theme");
  if (saved === "dark") {
    document.body.classList.add("dark");
  }

  if (btn) {
    btn.addEventListener("click", () => {
      const isDark = document.body.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
    });
  }
});
