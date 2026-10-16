import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

test("refund navigation opens its collapsed panel before scrolling", async () => {
  const calls = [];
  const panel = { tagName: "DETAILS", open: false, parentElement: null };
  const form = { tagName: "FORM", parentElement: panel,
    scrollIntoView() { calls.push(panel.open); } };
  const source = await readFile(new URL("../webapp/static/modules/home-navigation.js", import.meta.url), "utf8");
  const context = vm.createContext({ document: { getElementById: (id) => id === "refund" ? form : null } });
  vm.runInContext(source.replaceAll("export function", "function"), context);
  vm.runInContext("revealBudgetSection('refund'); revealBudgetSection('missing')", context);
  assert.equal(panel.open, true);
  assert.deepEqual(calls, [true]);
});
