import { element, refreshIcons } from "../modules/ui.js?v=20261001-3";
import { initLayout, renderLayout } from "./layout.js?v=20261002-3";
import { initMinigame, renderGame } from "./minigame.js?v=20261002-3";
import { renderModel } from "./appearance.js?v=20261002-3";

let clock, current;
const ages = ["Малыш", "Подросток", "Молодой", "Взрослый", "Легенда"];
const personalities = { robot: "Любознательный", cat: "Независимый", dragon: "Смелый", penguin: "Общительный", owl: "Вдумчивый" };

function atmosphere() {
  if (!current) return;
  const date = new Date(), hour = date.getHours();
  const light = hour < 6 || hour >= 22 ? "night" : hour >= 18 ? "evening" : "day";
  const activity = light === "night" ? current.pet === "owl" ? "study" : "sleep" : ["play", "study", "rest"][(Math.floor(date.getMinutes() / 5) + Object.keys(personalities).indexOf(current.pet)) % 3];
  const stage = document.getElementById("pet-stage"); stage.dataset.light = light; stage.dataset.activity = activity;
  const labels = { sleep: "Спит", play: "Играет", study: "Учится", rest: "Отдыхает" };
  document.getElementById("pet-mood").textContent = `${personalities[current.pet]} · ${labels[activity]}`;
}

function schedule() {
  clearInterval(clock);
  if (document.hidden || document.getElementById("tab-pets").hidden) return;
  atmosphere(); clock = setInterval(atmosphere, 60000);
}

export function renderLife(world) {
  const newGoal = current && world.album.some(entry => entry.event.startsWith("goal:") && !current.album.some(old => old.event === entry.event));
  current = world; atmosphere(); renderLayout(world); renderGame(world);
  document.getElementById("pet-season").textContent = world.season.name;
  const stage = document.getElementById("pet-stage"); stage.dataset.goal = String(world.goal_badge);
  if (newGoal) {
    for (let index = 0; index < 9; index++) {
      const spark = element("i", "goal-spark"); spark.dataset.lucide = "sparkles";
      spark.style.left = `${8 + index * 10}%`; spark.style.animationDelay = `${index * 50}ms`;
      spark.setAttribute("aria-hidden", "true"); stage.append(spark); setTimeout(() => spark.remove(), 2500);
    }
  }
  stage.querySelector(".goal-memento")?.remove();
  if (world.goal_badge) {
    const badge = element("i", "goal-memento"); badge.dataset.lucide = "award";
    badge.title = "Достигнутая цель накоплений"; badge.setAttribute("aria-label", badge.title); stage.append(badge);
  }
  const entries = ages.map((age, index) => {
    const earned = world.album.find(entry => entry.event === `age:${index + 1}`);
    const row = element("article", "pet-album-entry");
    const frame = element("span", "pet-model-frame"), image = element("img"); image.alt = ""; frame.append(image);
    if (earned) renderModel(frame, world.pet, index + 1);
    else { frame.replaceChildren(element("span", "", "—")); }
    const info = element("div", "", age); info.append(element("small", "", earned ? `Отмечено: ${earned.recorded_at}` : "Еще не открыт"));
    row.append(frame, info); return row;
  });
  for (const entry of world.album.filter(item => item.event.startsWith("goal:"))) {
    const row = element("article", "pet-album-entry", entry.title); row.append(element("small", "", entry.recorded_at)); entries.push(row);
  }
  document.getElementById("pet-album").replaceChildren(...entries); refreshIcons();
}

export function initLife(receive) {
  initLayout(receive); initMinigame(receive);
  for (const [button, dialog] of [["pet-album-open", "pet-album-dialog"], ["pet-game-open", "pet-game-dialog"]])
    document.getElementById(button).onclick = () => document.getElementById(dialog).showModal();
  for (const button of document.querySelectorAll("[data-close-dialog]")) button.onclick = () => document.getElementById(button.dataset.closeDialog).close();
  document.addEventListener("cash:tab", schedule); document.addEventListener("visibilitychange", schedule);
}
