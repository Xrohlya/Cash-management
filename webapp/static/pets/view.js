import { money } from "../modules/core.js?v=20261001-3";
import { element, refreshIcons } from "../modules/ui.js?v=20261001-3";
import { decorations } from "./decorations.js?v=20261002-2";
import { roomEvolution } from "./evolution.js?v=20261002-2";
import { renderAppearance } from "./appearance.js?v=20261002-2";

const node = (id) => document.getElementById(id);

export function renderWorld(world) {
  node("pet-name").textContent = world.display_name;
  node("pet-coins").textContent = world.coins;
  node("pet-room").textContent = world.room;
  node("pet-level").textContent = `Уровень ${world.level}`;
  node("pet-growth").textContent = `${world.age} · Глава ${world.chapter} · Рост ${Math.round(world.size / 1.05 * 100)}%`;
  node("pet-xp").textContent = `${world.xp} опыта`;
  node("pet-next-stage").textContent = `${world.stage === 3 ? "Следующая глава" : "Следующий этап"}: ${world.next_stage_xp}`;
  node("pet-progress").value = world.progress;
  node("pet-stage").dataset.pet = world.pet;
  node("pet-stage").dataset.stage = world.stage;
  node("pet-stage").style.setProperty("--chapter-hue", `${((world.chapter - 1) % 12) * 12}deg`);
  node("pet-stage").dataset.motion = Boolean(world.motion);
  node("pet-stage").setAttribute("aria-busy", "false");
  node("pet-character").disabled = false;
  renderAppearance(world);
  node("pet-room-image").src = `/static/pets/rooms/${world.pet}.svg`;
  node("pet-evolution").innerHTML = roomEvolution(world.pet);
  node("pet-custom-name").value = world.name;
  node("pet-motion").checked = Boolean(world.motion);
  node("pet-decorations").replaceChildren(...world.inventory.map((id) => {
    const decoration = decorations(id);
    decoration.dataset.tier = world.upgrades?.[id] || 1;
    return decoration;
  }));
  node("pet-picker").replaceChildren(...world.pets.map((pet) => {
    const button = element("button", "pet-choice");
    button.type = "button";
    button.dataset.petChoice = pet.id;
    button.setAttribute("aria-pressed", String(pet.id === world.pet));
    const image = element("img");
    image.src = `/static/pets/images/${pet.id}.png`;
    image.alt = "";
    image.width = 56;
    image.height = 56;
    image.loading = "lazy";
    button.append(image, element("span", "", pet.name));
    return button;
  }));
  node("pet-missions").replaceChildren(...world.missions.map((task) => {
    const row = element("article", "pet-mission");
    const info = element("div");
    info.append(element("strong", "", task.title), element("small", "", task.note || `+${task.xp} опыта · +${task.coins} монет`));
    const button = element("button", "", task.claimed ? "Получено" : task.id === "feed" ? "Покормить" : "Забрать");
    button.type = "button";
    button.dataset.petClaim = task.id;
    button.disabled = task.claimed || !task.eligible;
    button.title = task.claimed ? "Награда получена сегодня" : task.eligible ? "Получить награду" : "Условие пока не выполнено";
    row.append(info, button);
    return row;
  }));
  node("pet-shop").replaceChildren(...world.shop.map((item) => {
    const row = element("article", "pet-shop-item");
    const icon = element("i");
    icon.dataset.lucide = item.icon;
    const button = element("button", "", item.tier >= 3 ? "Максимум" : `${item.tier ? "Улучшить · " : ""}${item.cost}`);
    button.type = "button";
    button.dataset.petBuy = item.id;
    button.dataset.petTier = item.tier;
    button.title = item.tier >= 3 ? "Все три уровня открыты" : `Стоимость: ${item.cost} игровых монет`;
    button.disabled = item.tier >= 3 || world.coins < item.cost;
    row.append(icon, element("strong", "", item.name), element("small", "", `Уровень ${item.tier}/3 · монеты`), button);
    return row;
  }));
  refreshIcons();
}

export function renderPetFinance(dashboard) {
  const state = dashboard?.state;
  if (!state) return;
  node("pet-budget").textContent = money(state.available);
  node("pet-savings").textContent = money(state.savings);
  node("pet-goal-note").textContent = state.goal ? `Цель: ${money(state.goal.target)} · ${state.goal.progress}%` : "Цель накоплений пока не задана";
  node("pet-goal-progress").hidden = !state.goal;
  node("pet-goal-progress").value = state.goal?.progress || 0;
}
