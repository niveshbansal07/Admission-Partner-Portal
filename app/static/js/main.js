// Minimal JS placeholder.
// All critical business logic remains on the server.

document.addEventListener("click", (event) => {
  const btn = event.target.closest(".btn");
  if (!btn) return;

  // Simple ripple-like effect via scale
  btn.classList.add("btn-active");
  setTimeout(() => btn.classList.remove("btn-active"), 150);
});

