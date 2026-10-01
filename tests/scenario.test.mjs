import assert from "node:assert/strict";
import { test } from "node:test";
import { calculateScenario } from "../webapp/static/modules/scenario-math.js";

const budget = {
  state: { available: 1000, days_left: 10, savings: 300 },
  radar: { projected_balance: 900, reserved: 200, target_balance: 100, safe_today: 70 },
  planning: { expected_total: 5000 },
};

test("purchase calculation leaves real data untouched", () => {
  const before = JSON.stringify(budget);
  const result = calculateScenario(budget, 100);
  assert.equal(result.remaining, 900);
  assert.equal(result.safe, 60);
  assert.equal(result.projected, 800);
  assert.equal(result.risk, "yellow");
  assert.equal(JSON.stringify(budget), before);
});

test("unconfirmed income never makes an unaffordable purchase affordable now", () => {
  const result = calculateScenario(budget, 2000, "expense", true);
  assert.equal(result.risk, "red");
  assert.equal(result.remaining, -1000);
  assert.equal(result.projected, 3900);
  assert.equal(result.safe, 0);
});

test("savings scenarios show the new savings without writing an operation", () => {
  const result = calculateScenario(budget, 50, "save");
  assert.equal(result.savings, 350);
  assert.equal(result.risk, "green");
  assert.equal(budget.state.savings, 300);
});

test("invalid values and unknown operation types are rejected", () => {
  for (const value of [0, -1, NaN, Infinity, 1_000_000_001]) assert.throws(() => calculateScenario(budget, value));
  assert.throws(() => calculateScenario(budget, 1, "unknown"));
});
