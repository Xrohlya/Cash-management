import { telegram, initData, selectTab, showToast } from "./modules/core.js?v=20261011-1";
import { load } from "./modules/dashboard.js?v=20261011-1";
import { initSourcesActions } from "./modules/sources-actions.js?v=20261011-1";
import { initAccountsActions } from "./modules/accounts-actions.js?v=20261011-1";
import { initHistoryActions } from "./modules/history-actions.js?v=20261011-1";
import { initResetActions } from "./modules/reset-actions.js?v=20261011-1";
import { initOperationsActions } from "./modules/operations-actions.js?v=20261011-1";
import { initReceiptActions } from "./modules/receipt-actions.js?v=20261011-1";
import { initNavigationActions } from "./modules/navigation-actions.js?v=20261011-1";
import { initSettingsActions } from "./modules/settings-actions.js?v=20261011-1";
import { initRecurringActions } from "./modules/recurring-actions.js?v=20261011-1";
import { initPlansActions } from "./modules/plans-actions.js?v=20261011-1";
import { initLimitsActions } from "./modules/limits-actions.js?v=20261011-1";
import { initUndoActions } from "./modules/undo-actions.js?v=20261011-1";
import { initCalculators } from "./modules/calculators.js?v=20261011-1";
import { refreshIcons } from "./modules/ui.js?v=20261011-1";
import { initPetWorld } from "./pets/app.js?v=20261011-1";
import { initWallets } from "./modules/wallets.js?v=20261011-1";

initSourcesActions();
initAccountsActions();
initHistoryActions();
initResetActions();
initOperationsActions();
initReceiptActions();
initNavigationActions();
initSettingsActions();
initRecurringActions();
initPlansActions();
initLimitsActions();
initUndoActions();
initCalculators();
initPetWorld();
initWallets();
refreshIcons();
window.addEventListener("load", refreshIcons);

if (!initData) {
  document.getElementById("blocking-message").hidden = false;
} else {
  telegram?.ready();
  telegram?.expand();
  selectTab(sessionStorage.getItem("cash-management-tab") || "budget", false);
  load().catch((error) => showToast(error.message));
}
