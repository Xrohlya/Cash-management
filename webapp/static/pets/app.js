import { api, initData, money, showToast } from "../modules/core.js?v=20261001-3";
import { bindForm, requestConfirmation, runAction } from "../modules/ui.js?v=20261001-3";
import { store } from "../modules/store.js?v=20261001-3";
import { load } from "../modules/dashboard.js?v=20261001-3";
import { renderWorld, renderPetFinance } from "./view.js?v=20261002-3";
import { reactToPet } from "./animation.js?v=20261002-3";
import { petStore } from "./store.js?v=20261002-3";
import { previewColor, selectedColor } from "./appearance.js?v=20261002-3";
import { initLife } from "./life.js?v=20261002-3";

function receive(world) {
  petStore.world = world;
  renderWorld(world);
  renderPetFinance(store.dashboard);
}

async function refreshWorld() {
  if (!initData || petStore.loading) return;
  petStore.loading = true;
  const error = document.getElementById("pet-error");
  error.hidden = true;
  try { receive(await api("/api/pet")); }
  catch (exception) { error.textContent = `${exception.message} Нажмите «Обновить», чтобы повторить.`; error.hidden = false; }
  finally { petStore.loading = false; }
}

const post = (path, body) => api(`/api/pet/${path}`, { method: "POST", body: JSON.stringify(body) });

export function initPetWorld() {
  initLife(receive);
  const settingsDialog = document.getElementById("pet-settings-dialog");
  document.getElementById("pet-open-settings").addEventListener("click", () => settingsDialog.showModal());
  document.getElementById("pet-close-settings").addEventListener("click", () => settingsDialog.close());
  document.getElementById("pet-colors").addEventListener("change", () => previewColor(selectedColor()));
  settingsDialog.addEventListener("close", () => { if (petStore.world) previewColor(petStore.world.color); });
  document.addEventListener("cash:tab", (event) => { if (event.detail === "pets") refreshWorld(); });
  document.addEventListener("cash:dashboard", (event) => {
    renderPetFinance(event.detail);
    if (!document.getElementById("tab-pets").hidden) refreshWorld();
  });
  document.getElementById("pet-character").addEventListener("click", reactToPet);
  document.getElementById("pet-picker").addEventListener("click", (event) => {
    const button = event.target.closest("[data-pet-choice]");
    if (!button || !petStore.world) return;
    runAction(button, async () => receive(await post("settings", { pet: button.dataset.petChoice, name: "", motion: Boolean(petStore.world.motion), color: selectedColor() })));
  });
  bindForm("pet-settings-form", async () => {
    if (!petStore.world) return;
    receive(await post("settings", { pet: petStore.world.pet, name: document.getElementById("pet-custom-name").value, motion: document.getElementById("pet-motion").checked, color: selectedColor() }));
    showToast("Настройки питомца сохранены");
    settingsDialog.close();
  });
  for (const [id, selector, action] of [["pet-missions", "petClaim", "claim"], ["pet-shop", "petBuy", "buy"]]) {
    document.getElementById(id).addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button?.dataset[selector]) return;
      runAction(button, async () => {
        const response = await post(action, { id: button.dataset[selector], expected_level: Number(button.dataset.petTier || 0) });
        receive(response.world);
        if (response.created) {
          reactToPet();
          showToast(button.dataset.petClaim === "feed" ? "Питомец поел. Настоящие деньги не списаны." : action === "claim" ? "Награда получена" : "Украшение появилось в комнате");
        }
      });
    });
  }
  let savingsRequest;
  bindForm("pet-save-form", async (form) => {
    const amount = Number(document.getElementById("pet-save-amount").value);
    if (!await requestConfirmation(`Перевести ${money(amount)} из основного бюджета в настоящие накопления? Это финансовая операция, не игровые монеты.`)) return;
    if (savingsRequest?.amount !== amount) savingsRequest = { amount, request_id: crypto.randomUUID() };
    await api("/api/save", { method: "POST", body: JSON.stringify({ ...savingsRequest, description: "Накопления · Мой мир" }) });
    savingsRequest = null;
    form.reset();
    await load();
    await refreshWorld();
    showToast("Накопления пополнены");
  });
}
