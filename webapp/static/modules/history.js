import { kindLabels, money, shortDate, operationWord } from "./core.js?v=20261017-2";

function renderHistory(items) {
  const root = document.getElementById("history");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Операций пока нет</p>';
    return;
  }
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("article");
    row.className = item.kind === "cancelled" ? "history-item cancelled" : "history-item";
    const title = document.createElement("strong");
    title.textContent = item.description || kindLabels[item.kind] || item.kind;
    const amount = document.createElement("b");
    const positive = item.kind === "income" || Number(item.amount) < 0;
    const transfer = item.wallet_operation === "transfer" || ["account_transfer", "account_return", "wallet_transfer"].includes(item.kind);
    amount.className = transfer ? "" : positive ? "positive" : "negative";
    amount.textContent = `${item.kind === "cancelled" || transfer ? "" : positive ? "+" : "−"}${money(Math.abs(item.amount))}`;
    const meta = document.createElement("time");
    const label = item.wallet_operation === "refund" ? "Возврат покупки" : item.wallet_operation === "transfer" ? "Перевод" : item.kind === "wallet_expense" ? "Расход с другого счёта" : kindLabels[item.kind] || item.kind;
    meta.textContent = `${label} · ${shortDate(item.created_at)}`;
    row.append(title, amount, meta);
    if (["expense", "wallet_expense"].includes(item.kind) && item.amount > 0) {
      const refund = document.createElement("button");
      refund.type = "button";
      refund.className = "history-edit";
      refund.textContent = "Возврат";
      refund.dataset.walletRefund = item.id;
      row.append(refund);
    }
    if (item.kind === "expense" && item.amount > 0 && (!item.wallet_operation || item.wallet_operation === "expense" && item.wallet === "main")) {
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "history-edit";
      edit.textContent = "Изменить";
      edit.dataset.expenseEdit = item.id;
      edit.dataset.expenseAmount = item.amount;
      edit.dataset.expenseDescription = item.description;
      row.append(edit);
    }
    return row;
  }));
}

function renderCategories(items) {
  const root = document.getElementById("categories");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Расходов в этом периоде пока нет</p>';
    return;
  }
  const maxAmount = Math.max(...items.map((item) => Number(item.amount || 0)), 1);
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("article");
    row.className = "category-item";
    const title = document.createElement("strong");
    title.textContent = item.name;
    const amount = document.createElement("b");
    amount.textContent = money(item.amount);
    const count = document.createElement("small");
    count.textContent = `${item.count} ${operationWord(item.count)}`;
    const bar = document.createElement("span");
    bar.className = "category-bar";
    bar.style.width = `${Math.max(4, Number(item.amount || 0) / maxAmount * 100)}%`;
    row.append(title, amount, count, bar);
    return row;
  }));
}

function renderDaily(items) {
  const root = document.getElementById("daily-chart");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Данных для графика пока нет</p>';
    return;
  }
  const max = Math.max(...items.map((item) => Number(item.amount || 0)), 1);
  root.replaceChildren(...items.slice(-14).map((item) => {
    const column = document.createElement("div");
    column.className = "day-column";
    column.title = `${item.date.split("-").reverse().join(".")}: ${money(item.amount)}`;
    const amount = document.createElement("small");
    amount.textContent = Math.round(item.amount).toLocaleString("ru-RU");
    const bar = document.createElement("i");
    bar.style.height = `${Math.max(5, Number(item.amount || 0) / max * 100)}%`;
    const label = document.createElement("span");
    label.textContent = item.date.slice(8, 10);
    column.append(amount, bar, label);
    return column;
  }));
}

export { renderHistory, renderCategories, renderDaily };
