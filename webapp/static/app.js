import { telegram, initData, selectTab, showToast } from "./modules/core.js?v=20261001-1";
import { load } from "./modules/dashboard.js?v=20261001-1";
import { initSourcesActions } from "./modules/sources-actions.js?v=20261001-1";
import { initAccountsActions } from "./modules/accounts-actions.js?v=20261001-1";
import { initHistoryActions } from "./modules/history-actions.js?v=20261001-1";
import { initResetActions } from "./modules/reset-actions.js?v=20261001-1";
import { initOperationsActions } from "./modules/operations-actions.js?v=20261001-1";
import { initReceiptActions } from "./modules/receipt-actions.js?v=20261001-1";
import { initNavigationActions } from "./modules/navigation-actions.js?v=20261001-1";
import { initSettingsActions } from "./modules/settings-actions.js?v=20261001-1";
import { initRecurringActions } from "./modules/recurring-actions.js?v=20261001-1";

initSourcesActions();
initAccountsActions();
initHistoryActions();
initResetActions();
initOperationsActions();
initReceiptActions();
initNavigationActions();
initSettingsActions();
initRecurringActions();

if (!initData) {
  document.getElementById("blocking-message").hidden = false;
} else {
  telegram?.ready();
  telegram?.expand();
  selectTab(sessionStorage.getItem("cash-management-tab") || "budget", false);
  load().catch((error) => showToast(error.message));
}
