import { api, money, showToast } from "./core.js?v=20261016-1";
import { bindForm, requestConfirmation } from "./ui.js?v=20261016-1";
import { load } from "./dashboard.js?v=20261016-1";

function fillSelect(id, options) {
  const select = document.getElementById(id);
  const previous = select.value;
  select.replaceChildren(...options.map(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    return option;
  }));
  if (options.some(([value]) => String(value) === previous)) select.value = previous;
  else if (id === "wallet-destination") select.value = "savings";
}

export function initWallets() {
  let refunds = [];
  function setRefundAmount() {
    const row = refunds.find((item) => String(item.id) === document.getElementById("wallet-original").value);
    const amount = document.getElementById("wallet-refund-amount");
    amount.value = row?.refundable || "";
    amount.max = row?.refundable || "0";
    document.querySelector("#wallet-refund-form button").disabled = !row;
  }
  document.addEventListener("cash:dashboard", ({ detail }) => {
    const options = [["main", `Основной · ${money(detail.state.available)}`], ["savings", `Накопления · ${money(detail.state.savings)}`], ...detail.accounts.map((row) => [`account:${row.id}`, `${row.name} · ${money(row.balance)}`])];
    for (const id of ["expense-wallet", "wallet-source", "wallet-destination"]) fillSelect(id, options);
    refunds = detail.refundable_expenses || [];
    fillSelect("wallet-original", refunds.map((row) => [row.id, `#${row.id} · ${row.description} · ${row.created_at.slice(0, 10)} · ${money(row.refundable)}`]));
    setRefundAmount();
  });
  document.getElementById("wallet-original").addEventListener("change", setRefundAmount);
  document.getElementById("history").addEventListener("click", (event) => {
    const button = event.target.closest("[data-wallet-refund]");
    if (!button) return;
    const row = refunds.find((item) => String(item.id) === button.dataset.walletRefund);
    if (!row) { showToast("Эта покупка уже возвращена полностью"); return; }
    document.querySelector('[data-tab-target="budget"]').click();
    document.getElementById("wallet-original").value = String(row.id);
    setRefundAmount();
    document.getElementById("wallet-refund-form").scrollIntoView({ behavior: "smooth", block: "center" });
    document.getElementById("wallet-refund-amount").focus({ preventScroll: true });
  });
  for (const [form, kind] of [["wallet-transfer-form", "transfer"], ["wallet-refund-form", "refund"]]) {
    let pending;
    bindForm(form, async () => {
      const body = kind === "transfer" ? {
        source: document.getElementById("wallet-source").value,
        destination: document.getElementById("wallet-destination").value,
        amount: Number(document.getElementById("wallet-transfer-amount").value),
      } : {
        original_id: Number(document.getElementById("wallet-original").value),
        amount: Number(document.getElementById("wallet-refund-amount").value),
      };
      if (!await requestConfirmation(`${kind === "transfer" ? "Перевести" : "Вернуть на исходный счёт"} ${money(body.amount)}?`)) return;
      const signature = JSON.stringify(body);
      if (pending?.signature !== signature) pending = { signature, request_id: crypto.randomUUID() };
      await api(`/api/wallets/${kind}`, { method: "POST", body: JSON.stringify({ ...body, request_id: pending.request_id }) });
      pending = null;
      await load();
      showToast(kind === "transfer" ? "Перевод выполнен. Доходы и расходы не увеличены." : "Возврат учтён, деньги вернулись на исходный счёт.");
    });
  }
}
