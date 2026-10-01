import { api, selectTab, showToast } from "./core.js?v=20261001-2";
import { load } from "./dashboard.js?v=20261001-2";
import { store } from "./store.js?v=20261001-2";
import { bindForm, runAction, requestConfirmation } from "./ui.js?v=20261001-2";

export function initLimitsActions() {
  document.getElementById("budget-limit-notice").addEventListener("click", () => {
    selectTab("expenses");
    document.querySelector(".limits-section").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  bindForm("category-limit-form", async (form) => {
    await api("/api/limits", { method: "POST", body: JSON.stringify({
      category: document.getElementById("limit-category").value.trim(),
      amount: Number(document.getElementById("limit-amount").value),
    }) });
    form.reset();
    await load();
    showToast("Лимит сохранён");
  });
  document.getElementById("category-limits-list").addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const name = button.dataset.limitEdit || button.dataset.limitDelete;
    if (button.dataset.limitEdit) {
      const limit = store.dashboard?.planning.limits.find((item) => item.category === name);
      if (!limit) return;
      document.getElementById("limit-category").value = limit.category;
      document.getElementById("limit-amount").value = limit.amount;
      document.getElementById("limit-amount").focus();
      return;
    }
    if (!name || !await requestConfirmation(`Удалить лимит «${name}»? Расходы останутся в истории.`)) return;
    runAction(button, async () => {
      await api("/api/limits/delete", { method: "POST", body: JSON.stringify({ category: name }) });
      await load();
      showToast("Лимит удалён");
    });
  });
}
