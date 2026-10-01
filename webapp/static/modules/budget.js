import { financialDay, targetBalance, money } from "./core.js?v=20261001-2";

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

export { renderState, renderProfile, renderGoal };
