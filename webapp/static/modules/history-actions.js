import { api, showToast } from "./core.js?v=20261001-3";
import { load } from "./dashboard.js?v=20261001-3";

function initHistoryActions() {
  document.getElementById("history").addEventListener("click", (event) => {
    const button = event.target.closest("[data-expense-edit]");
    if (!button) return;
    document.getElementById("edit-expense-id").value = button.dataset.expenseEdit;
    document.getElementById("edit-expense-amount").value = button.dataset.expenseAmount;
    document.getElementById("edit-expense-description").value = button.dataset.expenseDescription;
    document.getElementById("edit-expense-dialog").showModal();
  });

  document.getElementById("cancel-expense-edit").addEventListener("click", () => {
    document.getElementById("edit-expense-dialog").close();
  });

  document.getElementById("edit-expense-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(`/api/transactions/${document.getElementById("edit-expense-id").value}/edit`, {
        method: "POST",
        body: JSON.stringify({
          amount: Number(document.getElementById("edit-expense-amount").value),
          description: document.getElementById("edit-expense-description").value.trim(),
        }),
      });
      document.getElementById("edit-expense-dialog").close();
      await load();
      showToast("Расход исправлен");
    } catch (error) {
      showToast(error.message);
    }
  });
}

export { initHistoryActions };
