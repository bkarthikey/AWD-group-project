document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const field = document.getElementById(button.dataset.passwordToggle);
    if (!field) {
      return;
    }

    const shouldShow = field.type === "password";
    field.type = shouldShow ? "text" : "password";
    button.textContent = shouldShow ? "Hide" : "Show";
    button.setAttribute("aria-label", shouldShow ? "Hide password" : "Show password");
  });
});
