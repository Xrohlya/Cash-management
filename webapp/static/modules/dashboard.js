import { renderAccounts } from "./accounts.js?v=20261001-2";
import { renderState } from "./budget.js?v=20261001-2";
import { api } from "./core.js?v=20261001-2";
import { renderHistory, renderCategories, renderDaily } from "./history.js?v=20261001-2";
import { renderRadar } from "./radar.js?v=20261001-2";
import { renderRecurring, renderUpcomingPayment } from "./recurring.js?v=20261001-2";
import { renderSources, renderSourcesOverview } from "./sources.js?v=20261001-2";
import { store } from "./store.js?v=20261001-2";
import { renderPlans } from "./plans-view.js?v=20261001-2";
import { renderLimits } from "./limits-view.js?v=20261001-2";
import { renderWeekly } from "./weekly-view.js?v=20261001-2";
import { renderUndo } from "./undo-actions.js?v=20261001-2";
import { refreshCalculators } from "./calculators.js?v=20261001-2";
import { refreshIcons } from "./ui.js?v=20261001-2";
import { renderCalendar } from "./calendar.js?v=20261001-2";

let loadSequence = 0;

async function load() {
  const sequence = ++loadSequence;
  const dashboard = await api("/api/dashboard");
  if (sequence !== loadSequence) return;
  store.dashboard = dashboard;
  const { state, analytics, recurring, accounts } = dashboard;
  const history = [...dashboard.transactions, ...dashboard.planning.undo_history].sort((a, b) => b.created_at.localeCompare(a.created_at));
  const sources = dashboard.income_sources;
  renderState(state);
  renderRadar(dashboard.radar);
  renderHistory(history);
  renderCategories(analytics.categories);
  renderDaily(analytics.daily);
  renderRecurring(recurring);
  renderUpcomingPayment(recurring);
  renderSources(sources);
  renderSourcesOverview(sources);
  renderAccounts(accounts, state);
  document.getElementById("forecast-confirmed").textContent = document.getElementById("projected-balance").textContent.replace("Прогноз: ", "");
  renderPlans(dashboard.planning, sources);
  const expectedEvents = dashboard.planning.plans.filter((plan) => plan.source_available && plan.due_date >= state.period_start && plan.due_date <= state.period_end).map((plan) => ({ date: plan.due_date, title: plan.title, amount: plan.net, kind: "planned_income" }));
  renderCalendar([...dashboard.radar.calendar, ...expectedEvents].sort((a, b) => a.date.localeCompare(b.date)));
  renderLimits(dashboard.planning, state);
  renderWeekly(dashboard.planning.weekly);
  renderUndo(dashboard.planning.undo);
  refreshCalculators();
  refreshIcons();
}

export { load };
