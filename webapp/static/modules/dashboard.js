import { renderAccounts } from "./accounts.js?v=20261001-1";
import { renderState } from "./budget.js?v=20261001-1";
import { api } from "./core.js?v=20261001-1";
import { renderHistory, renderCategories, renderDaily } from "./history.js?v=20261001-1";
import { renderRadar } from "./radar.js?v=20261001-1";
import { renderRecurring, renderUpcomingPayment } from "./recurring.js?v=20261001-1";
import { renderSources, renderSourcesOverview } from "./sources.js?v=20261001-1";

async function load() {
  const dashboard = await api("/api/dashboard");
  const { state, analytics, recurring, accounts } = dashboard;
  const history = dashboard.transactions;
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
}

export { load };
