const telegram = window.Telegram?.WebApp;
const localInitData = ["127.0.0.1", "localhost"].includes(window.location.hostname)
  ? new URLSearchParams(window.location.search).get("initData") || ""
  : "";
const initData = telegram?.initData || localInitData;

const operationLabels = {
  expense: ["Записать расход", "Например, продукты"],
  income: ["Добавить доход", "Например, зарплата"],
  rent: ["Учесть квартиру", "Квартира"],
  save: ["Отложить", "Накопления"],
};

const kindLabels = {
  income: "Доход",
  mandatory: "Обязательный вычет",
  expense: "Расход",
  recurring: "Регулярный платёж",
  rent: "Квартира",
  save: "Накопления",
  account_transfer: "Перевод на счёт",
  account_return: "Возврат на основной",
};

let operationKind = "expense";
let toastTimer;

const tabs = new Set(["budget", "expenses", "settings"]);

function selectTab(tabName, remember = true) {
  const selected = tabs.has(tabName) ? tabName : "budget";
  document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
    const active = panel.dataset.tabPanel === selected;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });
  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    const active = button.dataset.tabTarget === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  const quickAdd = document.getElementById("quick-add");
  if (quickAdd) quickAdd.hidden = selected === "budget";
  if (remember) sessionStorage.setItem("cash-management-tab", selected);
}

const financialDay = document.getElementById("financial-day");
const targetBalance = document.getElementById("target-balance");
const recurringDay = document.getElementById("recurring-day");
for (let day = 1; day <= 28; day += 1) {
  const option = document.createElement("option");
  option.value = String(day);
  option.textContent = `${day}-го числа`;
  financialDay.append(option);
  recurringDay.append(option.cloneNode(true));
}
recurringDay.value = String(Math.min(new Date().getDate(), 28));

function money(value) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(value || 0)) + " ₽";
}

function shortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
}

function operationWord(count) {
  const lastTwo = count % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return "операций";
  if (count % 10 === 1) return "операция";
  if (count % 10 >= 2 && count % 10 <= 4) return "операции";
  return "операций";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Не удалось выполнить запрос.");
  return body;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function renderState(state) {
  document.getElementById("available").textContent = money(state.available);
  document.getElementById("daily-limit").textContent = money(state.daily_limit);
  document.getElementById("today").textContent = money(state.today);
  document.getElementById("budget").textContent = money(state.budget);
  document.getElementById("spent").textContent = money(state.spent);
  document.getElementById("recurring").textContent = money(state.recurring);
  document.getElementById("rent").textContent = money(state.rent);
  document.getElementById("savings").textContent = money(state.savings);
  document.getElementById("period").textContent = `${state.period_start.split("-").reverse().join(".")} — ${state.period_end.split("-").reverse().join(".")}`;
  document.getElementById("days-left").textContent = `${state.days_left} дн. до конца периода`;
  financialDay.value = String(state.financial_day || 20);
  targetBalance.value = String(state.target_balance || 0);
  renderProfile(state.profile);
  renderGoal(state.goal);
}

function renderProfile(profile) {
  const name = profile?.first_name || "Пользователь";
  const hour = new Date().getHours();
  const welcome = hour < 6 ? "Доброй ночи" : hour < 12 ? "Доброе утро" : hour < 18 ? "Добрый день" : "Добрый вечер";
  document.getElementById("greeting").textContent = `${welcome}, ${name}`;
  document.getElementById("avatar").textContent = name.trim().slice(0, 2).toLocaleUpperCase("ru-RU");
  document.getElementById("today-date").textContent = new Intl.DateTimeFormat("ru-RU", {
    weekday: "long", day: "numeric", month: "long",
  }).format(new Date());
}

function renderGoal(goal) {
  const root = document.getElementById("goal-summary");
  const clear = document.getElementById("clear-goal");
  clear.hidden = !goal;
  if (!goal) {
    root.className = "goal-summary empty-goal";
    root.textContent = "Цель пока не задана";
    return;
  }
  root.className = "goal-summary";
  root.innerHTML = `
    <div><strong>${money(goal.current)} из ${money(goal.target)}</strong><b>${goal.progress}%</b></div>
    <span class="goal-track"><i style="width:${Math.max(2, goal.progress)}%"></i></span>
    <small>Срок: ${goal.target_date.split("-").reverse().join(".")}</small>`;
  document.getElementById("goal-target").value = goal.target;
  document.getElementById("goal-date").value = goal.target_date;
}

function renderRadar(radar) {
  document.getElementById("safe-today").textContent = money(radar.safe_today);
  document.getElementById("reserved-total").textContent = money(radar.reserved);
  document.getElementById("projected-balance").textContent = `Прогноз: ${money(radar.projected_balance)}`;
  document.getElementById("target-balance-radar").textContent = money(radar.target_balance);
  document.getElementById("streak-current").textContent = `${radar.streak.current} дн.`;
  document.getElementById("streak-best").textContent = `Рекорд: ${radar.streak.best} дн.`;
  document.getElementById("weekly-total").textContent = money(radar.weekly.current);

  const change = Number(radar.weekly.change_percent || 0);
  const weeklyChange = document.getElementById("weekly-change");
  if (radar.weekly.previous === 0 && radar.weekly.current === 0) {
    weeklyChange.textContent = "Расходов не было";
  } else if (change === 0) {
    weeklyChange.textContent = "Как неделю назад";
  } else {
    weeklyChange.textContent = `${change > 0 ? "+" : ""}${change.toLocaleString("ru-RU")}% к прошлой неделе`;
  }
  weeklyChange.className = change > 0 ? "trend-worse" : change < 0 ? "trend-better" : "";

  const pill = document.getElementById("risk-pill");
  pill.className = `risk-pill risk-${radar.risk}`;
  pill.textContent = radar.risk_title;
  document.getElementById("risk-text").textContent = radar.risk_text;

  const calendar = document.getElementById("money-calendar-list");
  if (!radar.calendar.length) {
    calendar.innerHTML = '<p class="empty compact-empty">Событий пока нет</p>';
    return;
  }
  calendar.replaceChildren(...radar.calendar.map((event) => {
    const row = document.createElement("article");
    row.className = `calendar-event calendar-${event.kind}`;
    const [year, month, day] = event.date.split("-").map(Number);
    const dateValue = new Date(year, month - 1, day);
    const dateBlock = document.createElement("time");
    dateBlock.dateTime = event.date;
    dateBlock.innerHTML = `<b>${day}</b><span>${new Intl.DateTimeFormat("ru-RU", { month: "short" }).format(dateValue)}</span>`;
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = event.title;
    const kind = document.createElement("small");
    kind.textContent = event.kind === "income" ? "Поступление" : event.kind === "payment" ? "Запланированный платёж" : "Граница периода";
    info.append(title, kind);
    row.append(dateBlock, info);
    if (Number(event.amount) > 0) {
      const amount = document.createElement("b");
      amount.textContent = `${event.kind === "income" ? "+" : "−"}${money(event.amount)}`;
      row.append(amount);
    }
    return row;
  }));
}

function renderHistory(items) {
  const root = document.getElementById("history");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Операций пока нет</p>';
    return;
  }
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("article");
    row.className = "history-item";
    const title = document.createElement("strong");
    title.textContent = item.description || kindLabels[item.kind] || item.kind;
    const amount = document.createElement("b");
    const positive = item.kind === "income";
    amount.className = positive ? "positive" : "negative";
    amount.textContent = `${positive ? "+" : "−"}${money(item.amount)}`;
    const meta = document.createElement("time");
    meta.textContent = `${kindLabels[item.kind] || item.kind} · ${shortDate(item.created_at)}`;
    row.append(title, amount, meta);
    if (item.kind === "expense") {
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

function renderRecurring(items) {
  const root = document.getElementById("recurring-list");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Регулярных платежей пока нет</p>';
    return;
  }
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("article");
    row.className = "recurring-item";
    row.innerHTML = `<div><strong></strong><small></small></div><b></b>`;
    row.querySelector("strong").textContent = item.title;
    row.querySelector("small").textContent = `${item.day_of_month}-го числа · ${item.kind === "rent" ? "Квартира" : "Расход"}`;
    row.querySelector("b").textContent = money(item.amount);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete-button";
    remove.dataset.recurringDelete = item.id;
    remove.setAttribute("aria-label", `Удалить ${item.title}`);
    remove.title = "Удалить";
    remove.textContent = "×";
    row.append(remove);
    return row;
  }));
}

function renderUpcomingPayment(items) {
  const root = document.getElementById("upcoming-payment");
  const active = items.filter((item) => Number(item.active));
  if (!active.length) {
    root.hidden = true;
    return;
  }
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const upcoming = active.map((item) => {
    let due = new Date(now.getFullYear(), now.getMonth(), Number(item.day_of_month));
    if (due < today) due = new Date(now.getFullYear(), now.getMonth() + 1, Number(item.day_of_month));
    return { item, due };
  }).sort((a, b) => a.due - b.due)[0];
  document.getElementById("upcoming-title").textContent = upcoming.item.title;
  document.getElementById("upcoming-amount").textContent = money(upcoming.item.amount);
  document.getElementById("upcoming-date").textContent = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric", month: "long",
  }).format(upcoming.due);
  root.hidden = false;
}

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

async function load() {
  const dashboard = await api("/api/dashboard");
  const { state, analytics, recurring, accounts } = dashboard;
  const history = dashboard.transactions;
  const sources = dashboard.income_sources;
  renderState(state);
  renderRadar(dashboard.radar);
  renderHistory(history);
  renderCategories(analytics.categories);
  renderDaily(analytics.daily);
  renderRecurring(recurring);
  renderUpcomingPayment(recurring);
  renderSources(sources);
  renderSourcesOverview(sources);
  renderAccounts(accounts, state);
}

function resetSourceForm() {
  document.getElementById("source-form").reset();
  document.getElementById("source-id").value = "";
  document.getElementById("save-source").textContent = "Добавить источник";
  document.getElementById("cancel-source").hidden = true;
}

document.getElementById("source-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = document.getElementById("source-id").value;
  const button = document.getElementById("save-source");
  button.disabled = true;
  try {
    const items = await api(`/api/income-sources${id ? `/${id}` : ""}`, {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("source-name").value.trim(),
        withholding_percent: Number(document.getElementById("source-percent").value),
      }),
    });
    renderSources(items);
    renderSourcesOverview(items);
    resetSourceForm();
    showToast(id ? "Источник обновлён" : "Источник добавлен");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("cancel-source").addEventListener("click", resetSourceForm);

document.getElementById("sources-list").addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-source-edit]");
  if (edit) {
    document.getElementById("source-id").value = edit.dataset.sourceEdit;
    document.getElementById("source-name").value = edit.dataset.sourceName;
    document.getElementById("source-percent").value = edit.dataset.sourcePercent;
    document.getElementById("save-source").textContent = "Сохранить";
    document.getElementById("cancel-source").hidden = false;
    document.getElementById("source-name").focus();
    return;
  }
  const remove = event.target.closest("[data-source-delete]");
  if (!remove || !window.confirm("Удалить источник дохода? История останется сохранена.")) return;
  try {
    const items = await api(`/api/income-sources/${remove.dataset.sourceDelete}/delete`, { method: "POST" });
    renderSources(items);
    renderSourcesOverview(items);
    showToast("Источник удалён");
  } catch (error) {
    showToast(error.message);
  }
});

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
  if (!button || !window.confirm("Удалить дополнительный счёт?")) return;
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

document.getElementById("history").addEventListener("click", (event) => {
  const button = event.target.closest("[data-expense-edit]");
  if (!button) return;
  document.getElementById("edit-expense-id").value = button.dataset.expenseEdit;
  document.getElementById("edit-expense-amount").value = button.dataset.expenseAmount;
  document.getElementById("edit-expense-description").value = button.dataset.expenseDescription;
  document.getElementById("edit-expense-dialog").showModal();
});

document.getElementById("cancel-expense-edit").addEventListener("click", () => {
  document.getElementById("edit-expense-dialog").close();
});

document.getElementById("edit-expense-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api(`/api/transactions/${document.getElementById("edit-expense-id").value}/edit`, {
      method: "POST",
      body: JSON.stringify({
        amount: Number(document.getElementById("edit-expense-amount").value),
        description: document.getElementById("edit-expense-description").value.trim(),
      }),
    });
    document.getElementById("edit-expense-dialog").close();
    await load();
    showToast("Расход исправлен");
  } catch (error) {
    showToast(error.message);
  }
});

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

document.querySelectorAll("[data-quick-expense]").forEach((button) => {
  button.addEventListener("click", () => {
    operationKind = "expense";
    document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item.dataset.kind === "expense"));
    document.getElementById("description").value = button.dataset.quickExpense;
    document.getElementById("submit").textContent = operationLabels.expense[0];
    document.getElementById("amount").focus();
    telegram?.HapticFeedback?.selectionChanged?.();
  });
});

function loadReceiptOcr() {
  if (window.Tesseract) return Promise.resolve(window.Tesseract);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
    script.onload = () => resolve(window.Tesseract);
    script.onerror = () => reject(new Error("Не удалось загрузить распознавание чека"));
    document.head.append(script);
  });
}

function receiptAmount(text) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const amountPattern = /(?:\d{1,3}(?:[\s.]\d{3})*|\d+)(?:[,.]\d{2})?/g;
  const decimalPattern = /(?:\d{1,3}(?:[\s.]\d{3})*|\d+)[,.]\d{2}/g;
  const values = (linesToRead, pattern) => linesToRead.flatMap((line) =>
    (line.match(pattern) || []).map((value) => Number(value.replace(/[\s.](?=\d{3})/g, "").replace(",", ".")))
  ).filter((value) => Number.isFinite(value) && value > 0 && value < 1_000_000);
  const preferred = lines.filter((line) => /итого|к оплате|сумма|total|оплачено/i.test(line));
  const totals = values(preferred, amountPattern);
  if (totals.length) return Math.max(...totals);
  const candidates = values(lines.filter((line) => !/инн|кассир|чек|дата|смена/i.test(line)), decimalPattern);
  return candidates.length ? Math.max(...candidates) : null;
}

function receiptCategory(text) {
  const value = text.toLocaleLowerCase("ru-RU");
  const groups = [
    ["Еда", ["продукт", "пятероч", "перекрест", "вкусвилл", "магнит", "лента", "ашан", "молоко", "хлеб", "кофе", "кафе", "ресторан"]],
    ["Транспорт", ["такси", "бензин", "топливо", "парков", "метро", "автобус"]],
    ["Здоровье", ["аптек", "лекар", "клиник", "медицин"]],
    ["Дом и связь", ["интернет", "мобильн", "телефон", "хозтовар", "ремонт"]],
    ["Подписки", ["подписк", "онлайн-сервис", "subscription"]],
    ["Одежда", ["одежд", "обув", "fashion"]],
  ];
  return groups.find(([, words]) => words.some((word) => value.includes(word)))?.[0] || "Разное";
}

document.getElementById("scan-receipt").addEventListener("click", () => {
  document.getElementById("receipt-photo").click();
});

document.getElementById("receipt-photo").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const status = document.getElementById("receipt-status");
  const button = document.getElementById("scan-receipt");
  button.disabled = true;
  status.textContent = "Подготавливаю распознавание…";
  try {
    const tesseract = await loadReceiptOcr();
    const result = await tesseract.recognize(file, "rus+eng", {
      logger: (progress) => {
        if (progress.status === "recognizing text") {
          status.textContent = `Читаю чек: ${Math.round(progress.progress * 100)}%`;
        }
      },
    });
    const text = result.data?.text || "";
    const amount = receiptAmount(text);
    if (!amount) throw new Error("Не удалось найти итоговую сумму. Введите её вручную.");
    operationKind = "expense";
    document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item.dataset.kind === "expense"));
    document.getElementById("submit").textContent = operationLabels.expense[0];
    document.getElementById("amount").value = amount.toFixed(2);
    document.getElementById("description").value = receiptCategory(text);
    status.textContent = "Чек распознан. Проверьте сумму перед записью.";
    telegram?.HapticFeedback?.notificationOccurred?.("success");
  } catch (error) {
    status.textContent = error.message;
    showToast(error.message);
  } finally {
    button.disabled = false;
    event.target.value = "";
  }
});

document.getElementById("operation-kind").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-kind]");
  if (!button) return;
  operationKind = button.dataset.kind;
  document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item === button));
  document.getElementById("submit").textContent = operationLabels[operationKind][0];
  document.getElementById("description").placeholder = operationLabels[operationKind][1];
});

document.querySelectorAll("button[data-tab-target]").forEach((button) => {
  button.addEventListener("click", () => {
    selectTab(button.dataset.tabTarget);
    telegram?.HapticFeedback?.selectionChanged?.();
  });
});

document.getElementById("operation-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = document.getElementById("submit");
  submit.disabled = true;
  try {
    const payload = {
      amount: Number(document.getElementById("amount").value),
      description: document.getElementById("description").value.trim(),
      request_id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    };
    const state = await api(`/api/${operationKind}`, { method: "POST", body: JSON.stringify(payload) });
    renderState(state);
    const [history, analytics] = await Promise.all([
      api("/api/transactions?limit=30"),
      api("/api/analytics"),
    ]);
    renderHistory(history);
    renderCategories(analytics.categories);
    renderDaily(analytics.daily);
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

document.getElementById("refresh").addEventListener("click", () => load().catch((error) => showToast(error.message)));

document.getElementById("quick-add").addEventListener("click", () => {
  selectTab("budget");
  document.getElementById("operation-section").scrollIntoView({ behavior: "smooth", block: "start" });
  setTimeout(() => document.getElementById("amount").focus(), 260);
  telegram?.HapticFeedback?.selectionChanged?.();
});

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
    const [history, analytics] = await Promise.all([
      api("/api/transactions?limit=30"),
      api("/api/analytics"),
    ]);
    renderHistory(history);
    renderCategories(analytics.categories);
    renderDaily(analytics.daily);
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

document.getElementById("recurring-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  try {
    const items = await api("/api/recurring", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("recurring-title").value.trim(),
        amount: Number(document.getElementById("recurring-amount").value),
        kind: document.getElementById("recurring-kind").value,
        day_of_month: Number(recurringDay.value),
      }),
    });
    renderRecurring(items);
    event.target.reset();
    recurringDay.value = String(Math.min(new Date().getDate(), 28));
    await load();
    showToast("Регулярный платёж добавлен");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("recurring-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-recurring-delete]");
  if (!button || !window.confirm("Удалить регулярный платёж?")) return;
  try {
    const items = await api(`/api/recurring/${button.dataset.recurringDelete}/delete`, { method: "POST" });
    renderRecurring(items);
    showToast("Платёж удалён");
  } catch (error) {
    showToast(error.message);
  }
});

if (!initData) {
  document.getElementById("blocking-message").hidden = false;
} else {
  telegram.ready();
  telegram.expand();
  selectTab(sessionStorage.getItem("cash-management-tab") || "budget", false);
  load().catch((error) => showToast(error.message));
}
