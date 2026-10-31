const palette = ["#42c7ff", "#63e4b1", "#f0c66b", "#f38cb5", "#a9a0ff", "#7ed7d0"];
const currency = (value) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value) + " ₽";
const dayMs = 86400000;

export function dailyData(analytics, range = 14) {
  const start = Date.parse(`${analytics.period_start}T00:00:00Z`);
  const end = Math.min(Date.parse(`${analytics.period_end}T00:00:00Z`), Date.parse(`${analytics.as_of}T00:00:00Z`));
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return [];
  const amounts = new Map(analytics.daily.map((item) => [item.date, Number(item.amount)]));
  const first = range ? Math.max(start, end - (range - 1) * dayMs) : start;
  const result = [];
  for (let stamp = first; stamp <= end; stamp += dayMs) {
    const date = new Date(stamp).toISOString().slice(0, 10);
    result.push({ date, amount: amounts.get(date) || 0 });
  }
  return result;
}

function base(description, reducedMotion) {
  return {
    animation: !reducedMotion, animationDuration: 350,
    backgroundColor: "transparent", textStyle: { fontFamily: "system-ui, sans-serif", color: "#98a8ba" },
    aria: { enabled: true, label: { description } },
    tooltip: { trigger: "axis", renderMode: "richText", confine: true,
      backgroundColor: "#131d2a", borderColor: "#355571", textStyle: { color: "#eff6ff", fontSize: 12 },
      valueFormatter: currency },
    grid: { left: 12, right: 18, top: 20, bottom: 12, containLabel: true },
  };
}

export function dailyOption(items, reducedMotion = false) {
  return {
    ...base("Расходы и возвраты по дням. Суммы в рублях.", reducedMotion),
    xAxis: { type: "category", data: items.map((item) => item.date.slice(5).split("-").reverse().join(".")),
      axisTick: { show: false }, axisLine: { lineStyle: { color: "#263342" } },
      axisLabel: { fontSize: 10, hideOverlap: true } },
    yAxis: { type: "value", name: "₽", splitNumber: 4,
      splitLine: { lineStyle: { color: "#202c3a" } },
      axisLabel: { fontSize: 10, formatter: (value) => Math.abs(value) >= 1000 ? `${value / 1000}к` : String(value) } },
    series: [{ name: "Расходы с учётом возвратов", type: "bar", barMaxWidth: 24,
      data: items.map((item) => ({ value: item.amount, itemStyle: {
        color: item.amount < 0 ? "#63e4b1" : "#42c7ff", borderRadius: item.amount < 0 ? [0, 0, 3, 3] : [3, 3, 0, 0],
      } })), emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "#42c7ff66" } } }],
  };
}

export function categoriesOption(items, reducedMotion = false) {
  return {
    ...base("Расходы и возвраты по категориям. Точные суммы есть в списке ниже.", reducedMotion),
    yAxis: { type: "category", inverse: true, data: items.map((item) => item.name),
      axisTick: { show: false }, axisLine: { show: false },
      axisLabel: { fontSize: 11, width: 100, overflow: "truncate" } },
    xAxis: { type: "value", splitNumber: 3, axisLabel: { fontSize: 10, hideOverlap: true },
      splitLine: { lineStyle: { color: "#202c3a" } } },
    dataZoom: items.length > 12 ? [{ type: "slider", yAxisIndex: 0, start: 0,
      end: 12 / items.length * 100, width: 8, right: 0, showDetail: false,
      borderColor: "#263342", fillerColor: "#42c7ff33" }] : [],
    series: [{ name: "С учётом возвратов", type: "bar", barMaxWidth: 18,
      data: items.map((item, index) => ({ value: Number(item.amount), itemStyle: {
        color: Number(item.amount) < 0 ? "#63e4b1" : palette[index % palette.length], borderRadius: 3,
      } })), emphasis: { focus: "self" } }],
  };
}
