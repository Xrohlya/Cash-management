import { money, selectTab, showToast } from "./core.js?v=20261001-3";
import { store } from "./store.js?v=20261001-3";
import { calculateScenario } from "./scenario-math.js?v=20261001-3";
import { element } from "./ui.js?v=20261001-3";

function renderResult(id, amount, kind, includeIncome) {
  if (!store.dashboard) throw new Error("Сначала дождитесь загрузки бюджета");
  const result = calculateScenario(store.dashboard, amount, kind, includeIncome);
  const root = document.getElementById(id);
  root.hidden = false;
  root.dataset.risk = result.risk;
  const details = element("dl");
  const rows = [["Свободно после операции", money(result.remaining)], ["Лимит на день", `${money(result.currentSafe)} → ${money(result.safe)}`], ["Прогноз к концу периода", money(result.projected)]];
  if (kind === "save") rows.push(["В накоплениях", money(result.savings)]);
  if (includeIncome) rows.push(["Ожидаемые поступления", money(result.planned)]);
  rows.forEach(([label, value]) => details.append(element("dt", "", label), element("dd", "", value)));
  root.replaceChildren(element("strong", "", result.title), details, element("p", "financial-note", "Расчёт без изменения баланса"));
}

function runCalculator(type) {
  const scenario = type === "scenario";
  renderResult(`${type}-result`, Number(document.getElementById(`${type}-amount`).value),
    scenario ? document.getElementById("scenario-kind").value : "expense",
    scenario && document.getElementById("scenario-income").checked);
}

export function refreshCalculators() {
  for (const type of ["afford", "scenario"]) {
    if (!document.getElementById(`${type}-result`).hidden) {
      try { runCalculator(type); } catch { document.getElementById(`${type}-result`).hidden = true; }
    }
  }
}

export function initCalculators() {
  for (const type of ["afford", "scenario"]) {
    document.getElementById(`${type}-form`).addEventListener("submit", (event) => {
      event.preventDefault();
      try { runCalculator(type); } catch (error) { showToast(error.message); }
    });
  }
  document.querySelectorAll("[data-planning-jump]").forEach((button) => button.addEventListener("click", () => {
    selectTab("plans");
    document.getElementById(button.dataset.planningJump).scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}
