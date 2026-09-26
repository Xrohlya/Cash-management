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
  if (remember) sessionStorage.setItem("cash-management-tab", selected);
}

const financialDay = document.getElementById("financial-day");
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
  renderGoal(state.goal);
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

async function load() {
  const [state, history, analytics, recurring] = await Promise.all([
    api("/api/state"),
    api("/api/transactions?limit=30"),
    api("/api/analytics"),
    api("/api/recurring"),
  ]);
  renderState(state);
  renderHistory(history);
  renderCategories(analytics.categories);
  renderDaily(analytics.daily);
  renderRecurring(recurring);
}

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
