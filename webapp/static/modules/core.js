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
  cancelled: "Отмена операции",
};

const operation = { kind: "expense" };
let toastTimer;

const tabs = new Set(["budget", "expenses", "plans", "settings"]);

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

export { telegram, initData, operationLabels, kindLabels, operation, selectTab, financialDay, targetBalance, recurringDay, money, shortDate, operationWord, api, showToast };
