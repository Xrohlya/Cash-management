import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";

test("save mode hides receipt and comment, sends selected account", async () => {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: "", listeners: {}, classList: { toggle() {} },
      addEventListener(event, callback) { this.listeners[event] = callback; },
      focus() {}, reset() {},
    });
    return elements.get(id);
  };
  const calls = [];
  const context = vm.createContext({
    document: { getElementById: element, querySelectorAll: () => [] },
    operation: { kind: "expense" },
    operationLabels: { expense: ["Расход", ""], save: ["Отложить", ""] },
    telegram: null, crypto: { randomUUID: () => "test-request-id" },
    renderState() {}, load: async () => {}, showToast() {},
    api: async (url, options) => { calls.push([url, JSON.parse(options.body)]); return {}; },
  });
  const source = await readFile(new URL("../webapp/static/modules/operations-actions.js", import.meta.url), "utf8");
  vm.runInContext(source.replace(/^import .*;\n/gm, "").replace(/^export .*;$/gm, ""), context);
  vm.runInContext("initOperationsActions()", context);
  const choose = (kind) => element("operation-kind").listeners.click({
    target: { closest: () => ({ dataset: { kind } }) },
  });
  choose("save");
  assert.equal(element("operation-receipt-control").hidden, true);
  assert.equal(element("operation-description-control").hidden, true);
  assert.equal(element("save-destination-control").hidden, false);
  element("amount").value = "500";
  element("save-destination").value = "account:2";
  const submit = () => element("operation-form").listeners.submit({ preventDefault() {}, target: element("operation-form") });
  await submit();
  assert.equal(calls[0][0], "/api/wallets/transfer");
  assert.equal(calls[0][1].source, "main");
  assert.equal(calls[0][1].destination, "account:2");
  element("save-destination").value = "savings";
  await submit();
  assert.equal(calls[1][0], "/api/save");
  assert.equal(calls[1][1].description, "Накопления");
  choose("expense");
  assert.equal(element("operation-receipt-control").hidden, false);
  assert.equal(element("operation-description-control").hidden, false);
  assert.equal(element("save-destination-control").hidden, true);
});
