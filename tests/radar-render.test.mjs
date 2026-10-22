import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";

test("radar displays shared explanation and numeric breakdown", async () => {
  const nodes = new Map();
  const document = { getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, {});
    return nodes.get(id);
  } };
  const radar = {
    safe_today: 1960.57, reserved: 1500, projected_balance: -45976.94,
    target_balance: 1000, risk: "red", risk_title: "Высокий риск", risk_text: "Риск",
    streak: { current: 0, best: 1 }, weekly: { current: 11125, previous: 0 },
    explanation: { title: "Не хватит 45 977 ₽", pace: "Темп за 3 дня", guidance: "Лимит", notice: "Не долг", target_gap: "" },
    calculation: { available: 59356.39, period_spending: 11125, elapsed_days: 3, daily_average: 3708.33, forecast_days: 28, future_spending: 103833.33 },
  };
  const source = await readFile(new URL("../webapp/static/modules/radar.js", import.meta.url), "utf8");
  const context = vm.createContext({ document, radar, money: (value) => `${value} ₽` });
  vm.runInContext(source.replace(/^import .*;\n/gm, "").replace(/^export .*;$/gm, ""), context);
  vm.runInContext("renderRadar(radar)", context);
  assert.equal(nodes.get("projected-balance").textContent, radar.explanation.title);
  assert.equal(nodes.get("radar-calc-elapsed").textContent, "3");
  assert.equal(nodes.get("radar-target-gap").hidden, true);
  assert.equal(nodes.get("radar-formula").textContent, "59356.39 ₽ − 1500 ₽ − 103833.33 ₽ = -45976.94 ₽");
});
