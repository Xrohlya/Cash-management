const telegram = window.Telegram?.WebApp;
const initData = telegram?.initData || "";

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
  rent: "Квартира",
  save: "Накопления",
};

let operationKind = "expense";
let toastTimer;

function money(value) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(value || 0)) + " ₽";
}

function shortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
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
  document.getElementById("rent").textContent = money(state.rent);
  document.getElementById("savings").textContent = money(state.savings);
  document.getElementById("period").textContent = `${state.period_start.split("-").reverse().join(".")} — ${state.period_end.split("-").reverse().join(".")}`;
  document.getElementById("days-left").textContent = `${state.days_left} дн. до конца периода`;
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

async function load() {
  const [state, history] = await Promise.all([api("/api/state"), api("/api/transactions?limit=30")]);
  renderState(state);
  renderHistory(history);
}

document.getElementById("operation-kind").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-kind]");
  if (!button) return;
  operationKind = button.dataset.kind;
  document.querySelectorAll("#operation-kind button").forEach((item) => item.classList.toggle("active", item === button));
  document.getElementById("submit").textContent = operationLabels[operationKind][0];
  document.getElementById("description").placeholder = operationLabels[operationKind][1];
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
    renderHistory(await api("/api/transactions?limit=30"));
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

if (!initData) {
  document.getElementById("blocking-message").hidden = false;
} else {
  telegram.ready();
  telegram.expand();
  load().catch((error) => showToast(error.message));
}
