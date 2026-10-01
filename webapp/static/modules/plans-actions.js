import { api, money, showToast } from "./core.js?v=20261001-3";
import { load } from "./dashboard.js?v=20261001-3";
import { store } from "./store.js?v=20261001-3";
import { bindForm, runAction, requestConfirmation } from "./ui.js?v=20261001-3";

function resetPlanForm() {
  document.getElementById("planned-income-form").reset();
  document.getElementById("planned-income-id").value = "";
  document.getElementById("save-planned-income").textContent = "Добавить поступление";
  document.getElementById("cancel-planned-income-edit").hidden = true;
}

export function initPlansActions() {
  bindForm("planned-income-form", async () => {
    const id = document.getElementById("planned-income-id").value;
    const source = document.getElementById("planned-income-source").value;
    await api(`/api/plans${id ? `/${id}/edit` : ""}`, {
      method: "POST", body: JSON.stringify({
        title: document.getElementById("planned-income-title").value.trim(),
        amount: Number(document.getElementById("planned-income-amount").value),
        due_date: document.getElementById("planned-income-date").value,
        source_id: source ? Number(source) : null,
      }),
    });
    resetPlanForm();
    await load();
    showToast("План сохранён. Баланс не изменён.");
  });
  document.getElementById("cancel-planned-income-edit").addEventListener("click", resetPlanForm);
  document.getElementById("planned-income-list").addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) return;
    const id = button.dataset.planEdit || button.dataset.planConfirm || button.dataset.planCancel;
    const plan = store.dashboard?.planning.plans.find((item) => String(item.id) === id);
    if (!plan) return;
    if (button.dataset.planEdit) {
      document.getElementById("planned-income-id").value = plan.id;
      document.getElementById("planned-income-title").value = plan.title;
      document.getElementById("planned-income-amount").value = plan.amount;
      document.getElementById("planned-income-date").value = plan.due_date;
      document.getElementById("planned-income-source").value = plan.source_available ? String(plan.source_id || "") : "";
      document.getElementById("save-planned-income").textContent = "Сохранить изменения";
      document.getElementById("cancel-planned-income-edit").hidden = false;
      document.getElementById("planned-income-form").scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    const received = Boolean(button.dataset.planConfirm);
    const question = received ? `Доход «${plan.title}» получен? На основной счёт поступит ${money(plan.net)}.` : `Убрать «${plan.title}» из ожидаемых доходов?`;
    if (!await requestConfirmation(question)) return;
    runAction(button, async () => {
      await api(`/api/plans/${id}/${received ? "confirm" : "cancel"}`, { method: "POST" });
      await load();
      showToast(received ? "Доход учтён в основном бюджете" : "Поступление убрано из плана");
    });
  });
}
