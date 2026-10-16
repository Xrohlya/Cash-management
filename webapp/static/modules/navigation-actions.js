import { telegram, operation, selectTab, showToast } from "./core.js?v=20261017-3";
import { load } from "./dashboard.js?v=20261017-3";
import { revealBudgetSection } from "./home-navigation.js?v=20261017-3";

function initNavigationActions() {
  document.querySelectorAll("button[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => {
      selectTab(button.dataset.tabTarget);
      window.scrollTo({ top: 0, behavior: "instant" });
      telegram?.HapticFeedback?.selectionChanged?.();
    });
  });

  document.getElementById("refresh").addEventListener("click", () => load().catch((error) => showToast(error.message)));

  document.getElementById("quick-add").addEventListener("click", () => {
    selectTab("budget");
    revealBudgetSection("operation-section");
    setTimeout(() => document.getElementById("amount").focus(), 260);
    telegram?.HapticFeedback?.selectionChanged?.();
  });
}

export { initNavigationActions };
