import { money } from "./core.js?v=20261001-2";

function renderAccounts(items, state) {
  const root = document.getElementById("accounts-summary");
  const primary = document.createElement("article");
  primary.className = "account-card primary-account";
  primary.innerHTML = `<div><strong>Основной</strong><small>Главный счёт</small></div><b>${money(state.available)}</b>`;
  const extra = items.map((item) => {
    const card = document.createElement("article");
    card.className = "account-card";
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.name;
    const hint = document.createElement("small");
    hint.textContent = "Дополнительный счёт";
    info.append(title, hint);
    const amount = document.createElement("b");
    amount.textContent = money(item.balance);
    const transfer = document.createElement("button");
    transfer.type = "button";
    transfer.className = "account-transfer-button";
    transfer.textContent = "Перевести";
    transfer.dataset.accountTransfer = item.id;
    transfer.dataset.accountName = item.name;
    card.append(info, amount, transfer);
    return card;
  });
  root.replaceChildren(primary, ...extra);

  document.getElementById("account-limit").textContent = `${items.length} из 3`;
  const settingsRoot = document.getElementById("accounts-settings-list");
  if (!items.length) {
    settingsRoot.innerHTML = '<p class="empty compact-empty">Дополнительных счетов пока нет</p>';
  } else {
    settingsRoot.replaceChildren(...items.map((item) => {
      const row = document.createElement("article");
      row.className = "account-settings-item";
      const label = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = item.name;
      const balance = document.createElement("small");
      balance.textContent = money(item.balance);
      label.append(name, balance);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "delete-button";
      remove.textContent = "×";
      remove.title = "Удалить";
      remove.dataset.accountDelete = item.id;
      row.append(label, remove);
      return row;
    }));
  }
  const createButton = document.querySelector("#account-form button");
  createButton.disabled = items.length >= 3;
}

export { renderAccounts };
