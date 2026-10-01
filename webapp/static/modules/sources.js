import { money } from "./core.js?v=20261001-3";

function renderSources(items) {
  const root = document.getElementById("sources-list");
  const active = items.filter((item) => Number(item.active));
  if (!active.length) {
    root.innerHTML = '<p class="empty">Создайте первый источник дохода</p>';
    return;
  }
  root.replaceChildren(...active.map((item) => {
    const row = document.createElement("article");
    row.className = "source-item";
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `${item.name} · ${Number(item.withholding_percent).toLocaleString("ru-RU")}%`;
    const totals = document.createElement("small");
    totals.textContent = `Доход ${money(item.gross_total)} · удержано ${money(item.withheld_total)}`;
    info.append(title, totals);
    const actions = document.createElement("div");
    actions.className = "source-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "✎";
    edit.title = "Изменить";
    edit.dataset.sourceEdit = item.id;
    edit.dataset.sourceName = item.name;
    edit.dataset.sourcePercent = item.withholding_percent;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "Удалить";
    remove.dataset.sourceDelete = item.id;
    actions.append(edit, remove);
    const command = document.createElement("div");
    command.className = "source-command";
    command.textContent = `Напишите боту: получил 30000 ${item.name.toLocaleLowerCase("ru-RU")}`;
    row.append(info, actions, command);
    return row;
  }));
}

function renderSourcesOverview(items) {
  const root = document.getElementById("sources-overview");
  const active = items.filter((item) => Number(item.active));
  if (!active.length) {
    root.innerHTML = '<p class="empty compact-empty">Источники добавляются в настройках</p>';
    return;
  }
  root.replaceChildren(...active.map((item) => {
    const row = document.createElement("article");
    row.className = "source-overview-item";
    const name = document.createElement("strong");
    name.textContent = item.name;
    const percent = document.createElement("small");
    percent.textContent = `Удержание ${Number(item.withholding_percent).toLocaleString("ru-RU")}%`;
    const total = document.createElement("b");
    total.textContent = money(item.gross_total);
    row.append(name, total, percent);
    return row;
  }));
}

export { renderSources, renderSourcesOverview };
