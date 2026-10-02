import { api, showToast } from "../modules/core.js?v=20261001-3";
import { requestConfirmation, runAction } from "../modules/ui.js?v=20261001-3";
import { petStore } from "./store.js?v=20261002-4";

export function initCharacterChange(receive) {
  const button = document.getElementById("pet-change-character");
  button.addEventListener("click", () => runAction(button, async () => {
    const world = petStore.world;
    const pet = document.getElementById("pet-new-character").value;
    if (!world || !pet || pet === world.pet) return;
    if (!await requestConfirmation("Сменить персонажа? Опыт, монеты, покупки, комната и все игровые достижения будут удалены. Финансы и история операций сохранятся.")) return;
    receive(await api("/api/pet/character", {
      method: "POST",
      body: JSON.stringify({ pet, expected_pet: world.pet, confirmation: "СМЕНИТЬ ПЕРСОНАЖА" }),
    }));
    showToast("Новый персонаж начинает с нуля. Финансы сохранены.");
  }));
}
