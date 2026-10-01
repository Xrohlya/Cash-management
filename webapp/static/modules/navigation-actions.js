import { telegram, operation, selectTab, showToast } from "./core.js?v=20261001-2";
import { load } from "./dashboard.js?v=20261001-2";

function initNavigationActions() {
  document.querySelectorAll("button[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => {
      selectTab(button.dataset.tabTarget);
      telegram?.HapticFeedback?.selectionChanged?.();
    });
  });

  document.getElementById("refresh").addEventListener("click", () => load().catch((error) => showToast(error.message)));

  document.getElementById("quick-add").addEventListener("click", () => {
    selectTab("budget");
    document.getElementById("operation-section").scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => document.getElementById("amount").focus(), 260);
    telegram?.HapticFeedback?.selectionChanged?.();
  });
}

export { initNavigationActions };
