import { renderState } from "./budget.js?v=20261016-1";
import { telegram, operationLabels, operation, api, showToast } from "./core.js?v=20261016-1";
import { load } from "./dashboard.js?v=20261016-1";

function initOperationsActions() {
  let pendingRequest;
  document.querySelectorAll("[data-quick-expense]").forEach((button) => {
    button.addEventListener("click", () => {
      operation.kind = "expense";
      document.getElementById("expense-wallet-control").hidden = false;
      document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item.dataset.kind === "expense"));
      document.getElementById("description").value = button.dataset.quickExpense;
      document.getElementById("submit").textContent = operationLabels.expense[0];
      document.getElementById("amount").focus();
      telegram?.HapticFeedback?.selectionChanged?.();
    });
  });

  document.getElementById("operation-kind").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-kind]");
    if (!button) return;
    operation.kind = button.dataset.kind;
    document.getElementById("expense-wallet-control").hidden = operation.kind !== "expense";
    document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item === button));
    document.getElementById("submit").textContent = operationLabels[operation.kind][0];
    document.getElementById("description").placeholder = operationLabels[operation.kind][1];
  });

  document.getElementById("operation-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = document.getElementById("submit");
    submit.disabled = true;
    try {
      const payload = {
        amount: Number(document.getElementById("amount").value),
        description: document.getElementById("description").value.trim(),
      };
      if (operation.kind === "expense") payload.wallet = document.getElementById("expense-wallet").value;
      const signature = JSON.stringify([operation.kind, payload]);
      if (pendingRequest?.signature !== signature) pendingRequest = { signature, id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}` };
      payload.request_id = pendingRequest.id;
      const state = await api(operation.kind === "expense" ? "/api/wallets/expense" : `/api/${operation.kind}`, { method: "POST", body: JSON.stringify(payload) });
      pendingRequest = null;
      renderState(state);
      await load();
      event.target.reset();
      telegram?.HapticFeedback?.notificationOccurred("success");
      showToast("Операция сохранена");
    } catch (error) {
      telegram?.HapticFeedback?.notificationOccurred("error");
      showToast(error.message);
    } finally {
      submit.disabled = false;
    }
  });
}

export { initOperationsActions };
