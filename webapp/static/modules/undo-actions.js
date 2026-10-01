import { api, kindLabels, money, showToast } from "./core.js?v=20261001-2";
import { load } from "./dashboard.js?v=20261001-2";
import { store } from "./store.js?v=20261001-2";
import { bindForm } from "./ui.js?v=20261001-2";

let confirmedId = null;

export function renderUndo(candidate) {
  const text = candidate?.allowed ? `${kindLabels[candidate.kind] || candidate.kind} · ${money(candidate.amount)} · ${candidate.description}` : candidate?.reason || "Операций для отмены пока нет";
  document.getElementById("undo-summary").textContent = text;
  document.getElementById("open-undo").disabled = !candidate?.allowed;
}

export function initUndoActions() {
  document.getElementById("open-undo").addEventListener("click", () => {
    const candidate = store.dashboard?.planning.undo;
    if (!candidate?.allowed) return;
    confirmedId = candidate.id;
    document.getElementById("undo-confirmation-text").textContent = `${candidate.description} · ${money(candidate.amount)}`;
    document.getElementById("undo-dialog").showModal();
  });
  document.getElementById("cancel-undo").addEventListener("click", () => document.getElementById("undo-dialog").close());
  bindForm("undo-form", async () => {
    if (!confirmedId) return;
    await api("/api/operations/undo", { method: "POST", body: JSON.stringify({ transaction_id: confirmedId, confirmed: true }) });
    confirmedId = null;
    document.getElementById("undo-dialog").close();
    await load();
    showToast("Операция отменена. Суммы восстановлены.");
  });
}
