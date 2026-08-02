// ----------------- TOAST NOTIFICATIONS -----------------
// Lightweight replacement for alert() with a nicer, non-blocking UI.
(function () {
  function ensureRoot() {
    let root = document.getElementById("toast-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "toast-root";
      document.body.appendChild(root);
    }
    return root;
  }

  window.toast = function (message, type = "info", duration = 3800) {
    const root = ensureRoot();
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${message}</span><span class="toast-close">&times;</span>`;
    root.appendChild(el);

    const remove = () => {
      el.style.transition = "opacity .2s ease, transform .2s ease";
      el.style.opacity = "0";
      el.style.transform = "translateX(8px)";
      setTimeout(() => el.remove(), 200);
    };

    el.querySelector(".toast-close").addEventListener("click", remove);
    if (duration) setTimeout(remove, duration);
    return el;
  };

  window.toastSuccess = (msg, d) => window.toast(msg, "success", d);
  window.toastError = (msg, d) => window.toast(msg, "error", d);
  window.toastInfo = (msg, d) => window.toast(msg, "info", d);
})();
