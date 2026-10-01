import { selectTab, api, showToast } from "./core.js?v=20261001-2";
import { load } from "./dashboard.js?v=20261001-2";

function initResetActions() {
  document.getElementById("open-reset").addEventListener("click", () => {
    document.getElementById("reset-form").reset();
    document.getElementById("reset-dialog").showModal();
  });

  document.getElementById("cancel-reset").addEventListener("click", () => {
    document.getElementById("reset-dialog").close();
  });

  document.getElementById("reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/reset", {
        method: "POST",
        body: JSON.stringify({ confirmation: document.getElementById("reset-confirmation").value }),
      });
      document.getElementById("reset-dialog").close();
      sessionStorage.removeItem("cash-management-tab");
      selectTab("budget");
      await load();
      showToast("Данные удалены. Начинаем с нуля.");
    } catch (error) {
      showToast(error.message);
    }
  });
}

export { initResetActions };
