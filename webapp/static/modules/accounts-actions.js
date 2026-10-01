import { api, showToast } from "./core.js?v=20261001-3";
import { load } from "./dashboard.js?v=20261001-3";
import { requestConfirmation } from "./ui.js?v=20261001-3";

function initAccountsActions() {
  document.getElementById("account-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      await api("/api/accounts", {
        method: "POST",
        body: JSON.stringify({ name: document.getElementById("account-name").value.trim() }),
      });
      event.target.reset();
      await load();
      showToast("Счёт создан");
    } catch (error) {
      showToast(error.message);
    } finally {
      if (document.getElementById("account-limit").textContent !== "3 из 3") button.disabled = false;
    }
  });

  document.getElementById("accounts-settings-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-account-delete]");
    if (!button || !await requestConfirmation("Удалить дополнительный счёт?")) return;
    try {
      await api(`/api/accounts/${button.dataset.accountDelete}/delete`, { method: "POST" });
      await load();
      showToast("Счёт удалён");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("accounts-summary").addEventListener("click", (event) => {
    const button = event.target.closest("[data-account-transfer]");
    if (!button) return;
    document.getElementById("account-transfer-form").reset();
    document.getElementById("account-transfer-id").value = button.dataset.accountTransfer;
    document.getElementById("account-transfer-title").textContent = `Счёт «${button.dataset.accountName}»`;
    document.getElementById("account-transfer-dialog").showModal();
  });

  document.getElementById("cancel-account-transfer").addEventListener("click", () => {
    document.getElementById("account-transfer-dialog").close();
  });

  document.getElementById("account-transfer-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      await api(`/api/accounts/${document.getElementById("account-transfer-id").value}/transfer`, {
        method: "POST",
        body: JSON.stringify({
          amount: Number(document.getElementById("account-transfer-amount").value),
          direction: document.getElementById("account-transfer-direction").value,
          request_id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        }),
      });
      document.getElementById("account-transfer-dialog").close();
      await load();
      showToast("Перевод выполнен");
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });
}

export { initAccountsActions };
