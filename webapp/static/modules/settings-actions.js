import { renderState } from "./budget.js?v=20261001-2";
import { telegram, financialDay, targetBalance, api, showToast } from "./core.js?v=20261001-2";
import { load } from "./dashboard.js?v=20261001-2";

function initSettingsActions() {
  document.getElementById("period-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.getElementById("save-period");
    button.disabled = true;
    try {
      const state = await api("/api/settings/period", {
        method: "POST",
        body: JSON.stringify({ financial_day: Number(financialDay.value) }),
      });
      renderState(state);
      await load();
      telegram?.HapticFeedback?.notificationOccurred("success");
      showToast("Период обновлён");
    } catch (error) {
      telegram?.HapticFeedback?.notificationOccurred("error");
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("radar-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.getElementById("save-radar");
    button.disabled = true;
    try {
      await api("/api/settings/radar", {
        method: "POST",
        body: JSON.stringify({ target_balance: Number(targetBalance.value) }),
      });
      await load();
      telegram?.HapticFeedback?.notificationOccurred("success");
      showToast("Желаемый остаток сохранён");
    } catch (error) {
      telegram?.HapticFeedback?.notificationOccurred("error");
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("goal-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      const state = await api("/api/goal", {
        method: "POST",
        body: JSON.stringify({
          target: Number(document.getElementById("goal-target").value),
          target_date: document.getElementById("goal-date").value,
        }),
      });
      renderState(state);
      showToast("Цель сохранена");
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("clear-goal").addEventListener("click", async () => {
    try {
      renderState(await api("/api/goal/clear", { method: "POST" }));
      document.getElementById("goal-form").reset();
      showToast("Цель удалена");
    } catch (error) {
      showToast(error.message);
    }
  });
}

export { initSettingsActions };
