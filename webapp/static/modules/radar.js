import { money } from "./core.js?v=20261001-3";

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

}

export { renderRadar };
