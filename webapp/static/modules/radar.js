import { money } from "./core.js?v=20261022-1";

function renderRadar(radar) {
  document.getElementById("safe-today").textContent = money(radar.safe_today);
  document.getElementById("reserved-total").textContent = money(radar.reserved);
  const { explanation, calculation } = radar;
  document.getElementById("projected-balance").textContent = explanation.title;
  document.getElementById("radar-pace").textContent = explanation.pace;
  document.getElementById("radar-guidance").textContent = explanation.guidance;
  document.getElementById("radar-notice").textContent = explanation.notice;
  const gap = document.getElementById("radar-target-gap");
  gap.textContent = explanation.target_gap;
  gap.hidden = !explanation.target_gap;
  for (const [id, value] of [
    ["available", money(calculation.available)],
    ["spending", money(calculation.period_spending)],
    ["elapsed", String(calculation.elapsed_days)],
    ["average", money(calculation.daily_average)],
    ["days", String(calculation.forecast_days)],
    ["reserved", money(radar.reserved)],
    ["future", money(calculation.future_spending)],
  ]) document.getElementById(`radar-calc-${id}`).textContent = value;
  document.getElementById("radar-formula").textContent = `${money(calculation.available)} − ${money(radar.reserved)} − ${money(calculation.future_spending)} = ${money(radar.projected_balance)}`;
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

}

export { renderRadar };
