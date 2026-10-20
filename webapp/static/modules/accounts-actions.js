import { api, showToast } from "./core.js?v=20261020-1";
import { load } from "./dashboard.js?v=20261020-1";
import { requestConfirmation } from "./ui.js?v=20261020-1";
import { revealBudgetSection } from "./home-navigation.js?v=20261020-1";

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
    document.getElementById("wallet-source").value = "main";
    document.getElementById("wallet-destination").value = `account:${button.dataset.accountTransfer}`;
    revealBudgetSection("wallet-transfer-panel");
    document.getElementById("wallet-transfer-amount").focus({ preventScroll: true });
  });
}

export { initAccountsActions };
