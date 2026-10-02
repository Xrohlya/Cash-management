import { api, showToast } from "../modules/core.js?v=20261001-3";
import { runAction } from "../modules/ui.js?v=20261001-3";

let editing = false, draft = {}, saved = {}, drag;
const stage = () => document.getElementById("pet-stage");
const items = () => [...document.querySelectorAll("#pet-decorations .room-item")];

export function renderLayout(world) {
  saved = world.layout;
  for (const item of items()) {
    const position = (editing ? draft : saved)[item.dataset.item];
    if (position) Object.assign(item.style, { left: `${position.x}%`, top: `${position.y}%`, bottom: "auto", right: "auto" });
    item.tabIndex = editing ? 0 : -1;
    item.setAttribute("role", editing ? "button" : "img");
    item.setAttribute("aria-label", world.shop.find(entry => entry.id === item.dataset.item)?.name || item.dataset.item);
  }
}

function mode(active) {
  editing = active;
  stage().classList.toggle("is-arranging", active);
  document.getElementById("pet-layout-save").hidden = !active;
  document.getElementById("pet-layout-cancel").hidden = !active;
  document.getElementById("pet-arrange").hidden = active;
  document.getElementById("pet-decorations").setAttribute("aria-hidden", String(!active));
  for (const item of items()) {
    item.tabIndex = active ? 0 : -1;
    item.setAttribute("role", active ? "button" : "img");
  }
}

function move(item, x, y) {
  const room = stage().getBoundingClientRect();
  const box = item.getBoundingClientRect();
  const position = { x: Math.max(0, Math.min(85, 100 - box.width / room.width * 100, x)), y: Math.max(5, Math.min(75, 90 - box.height / room.height * 100, y)) };
  draft[item.dataset.item] = position;
  Object.assign(item.style, { left: `${position.x}%`, top: `${position.y}%`, bottom: "auto", right: "auto" });
}

export function initLayout(receive) {
  document.getElementById("pet-arrange").onclick = () => {
    if (!items().length) return showToast("Сначала приобретите украшение");
    draft = structuredClone(saved);
    mode(true);
    showToast("Перетащите предметы или используйте стрелки");
  };
  document.getElementById("pet-layout-cancel").onclick = event => runAction(event.currentTarget, async () => { mode(false); receive(await api("/api/pet")); });
  document.getElementById("pet-layout-save").onclick = (event) => runAction(event.currentTarget, async () => {
    const world = await api("/api/pet/layout", { method: "POST", body: JSON.stringify({ positions: draft }) });
    mode(false); receive(world); showToast("Расстановка сохранена");
  });
  const layer = document.getElementById("pet-decorations");
  layer.addEventListener("pointerdown", (event) => {
    const item = event.target.closest(".room-item");
    if (!editing || !item) return;
    const room = stage().getBoundingClientRect(), box = item.getBoundingClientRect();
    drag = { item, dx: event.clientX - box.left, dy: event.clientY - box.top };
    item.setPointerCapture(event.pointerId); item.focus(); event.preventDefault();
  });
  layer.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const box = stage().getBoundingClientRect();
    move(drag.item, (event.clientX - box.left - drag.dx) / box.width * 100, (event.clientY - box.top - drag.dy) / box.height * 100);
  });
  for (const type of ["pointerup", "pointercancel"]) layer.addEventListener(type, () => { drag = null; });
  layer.addEventListener("keydown", (event) => {
    if (!editing || !event.target.dataset.item || !event.key.startsWith("Arrow")) return;
    event.preventDefault();
    const box = event.target.getBoundingClientRect(), room = stage().getBoundingClientRect();
    move(event.target, (box.left - room.left) / room.width * 100 + (event.key === "ArrowRight" ? 2 : event.key === "ArrowLeft" ? -2 : 0),
      (box.top - room.top) / room.height * 100 + (event.key === "ArrowDown" ? 2 : event.key === "ArrowUp" ? -2 : 0));
  });
}
