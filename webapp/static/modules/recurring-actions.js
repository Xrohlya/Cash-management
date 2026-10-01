import { recurringDay, api, showToast } from "./core.js?v=20261001-3";
import { load } from "./dashboard.js?v=20261001-3";
import { requestConfirmation } from "./ui.js?v=20261001-3";
import { renderRecurring } from "./recurring.js?v=20261001-3";

function initRecurringActions() {
  document.getElementById("recurring-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      const items = await api("/api/recurring", {
        method: "POST",
        body: JSON.stringify({
          title: document.getElementById("recurring-title").value.trim(),
          amount: Number(document.getElementById("recurring-amount").value),
          kind: document.getElementById("recurring-kind").value,
          day_of_month: Number(recurringDay.value),
        }),
      });
      renderRecurring(items);
      event.target.reset();
      recurringDay.value = String(Math.min(new Date().getDate(), 28));
      await load();
      showToast("Регулярный платёж добавлен");
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("recurring-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-recurring-delete]");
    if (!button || !await requestConfirmation("Удалить регулярный платёж?")) return;
    try {
      const items = await api(`/api/recurring/${button.dataset.recurringDelete}/delete`, { method: "POST" });
      renderRecurring(items);
      await load();
      showToast("Платёж удалён");
    } catch (error) {
      showToast(error.message);
    }
  });
}

export { initRecurringActions };
