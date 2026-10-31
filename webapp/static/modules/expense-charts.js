import { dailyData, dailyOption, categoriesOption } from "./chart-options.js?v=20261031-1";

let library, latest, range = 14;
const charts = new Map();

function loadLibrary() {
  if (window.echarts) return Promise.resolve(window.echarts);
  if (!library) library = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/static/vendor/echarts/echarts-6.0.0.min.js";
    script.onload = () => resolve(window.echarts);
    script.onerror = () => { script.remove(); library = null; reject(new Error("Chart library unavailable")); };
    document.head.append(script);
  });
  return library;
}

function visible() {
  return !document.getElementById("tab-expenses").hidden && !document.hidden;
}

function draw(id, items, option, echarts) {
  const element = document.getElementById(id);
  const notice = document.getElementById(`${id}-notice`);
  const hasData = items.some((item) => Number(item.amount) !== 0);
  notice.hidden = hasData;
  element.hidden = !hasData;
  notice.textContent = "Расходы за вычетом возвратов — 0 ₽";
  if (!hasData) {
    charts.get(id)?.clear();
    return;
  }
  if (!charts.has(id)) charts.set(id, echarts.init(element, null, { renderer: "canvas" }));
  const chart = charts.get(id);
  chart.resize();
  chart.setOption(option, { notMerge: true });
}

async function render() {
  if (!latest || !visible()) return;
  try {
    const echarts = await loadLibrary();
    if (!visible()) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const daily = dailyData(latest, range);
    const categories = latest.categories.filter((item) => Number(item.amount) !== 0);
    document.getElementById("category-chart").style.height = `${Math.max(220, Math.min(600, categories.length * 34 + 65))}px`;
    draw("daily-chart", daily, dailyOption(daily, reduced), echarts);
    draw("category-chart", categories, categoriesOption(categories, reduced), echarts);
    document.getElementById("charts-retry").hidden = true;
  } catch (error) {
    for (const id of ["daily-chart", "category-chart"]) {
      const notice = document.getElementById(`${id}-notice`);
      notice.hidden = false;
      notice.textContent = "Не удалось загрузить график";
    }
    document.getElementById("category-breakdown").open = true;
    document.getElementById("charts-retry").hidden = false;
    console.warn("Expense charts unavailable", error);
  }
}

export function renderExpenseCharts(analytics) {
  latest = analytics;
  render();
}

document.addEventListener("cash:tab", (event) => {
  if (event.detail === "expenses") requestAnimationFrame(render);
});
document.addEventListener("visibilitychange", () => { if (!document.hidden) render(); });
document.getElementById("chart-range").addEventListener("change", (event) => {
  range = Number(event.target.value);
  render();
});
document.getElementById("charts-retry").addEventListener("click", render);
const observer = new ResizeObserver(() => {
  if (visible()) for (const chart of charts.values()) chart.resize();
});
observer.observe(document.getElementById("expense-charts"));
