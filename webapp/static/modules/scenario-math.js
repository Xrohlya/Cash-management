"use strict";

export function calculateScenario(dashboard, amount, kind = "expense", includeIncome = false) {
  if (!Number.isFinite(amount) || amount <= 0 || amount > 1_000_000_000) throw new Error("Введите положительную сумму");
  if (!["expense", "save"].includes(kind)) throw new Error("Неизвестное действие");
  const { state, radar, planning } = dashboard;
  const round = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
  const remaining = round(state.available - amount);
  const planned = includeIncome ? planning.expected_total : 0;
  const projected = round(radar.projected_balance + planned - amount);
  const safe = round(Math.max(0, (remaining - radar.reserved - radar.target_balance) / Math.max(1, state.days_left)));
  let risk = "green";
  let title = kind === "save" ? "Можно отложить эту сумму" : "Покупка укладывается в бюджет";
  if (remaining < 0) {
    risk = "red";
    title = "Сейчас недостаточно свободных средств";
  } else if (projected < radar.target_balance) {
    risk = "yellow";
    title = "Желаемый остаток окажется под риском";
  } else if (amount > radar.safe_today) {
    risk = "yellow";
    title = "Сумма больше безопасного лимита на сегодня";
  }
  return { remaining, projected, safe, risk, title, currentSafe: radar.safe_today, planned,
    savings: round(state.savings + (kind === "save" ? amount : 0)) };
}
