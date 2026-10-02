import { api, showToast } from "../modules/core.js?v=20261001-3";
import { element, refreshIcons, runAction } from "../modules/ui.js?v=20261001-3";

let run, index = 0, ready = false, stepTimer, endTimer, claimed = false;
const node = id => document.getElementById(id);

function stop() {
  clearTimeout(stepTimer); clearTimeout(endTimer); ready = false; run = null;
  for (const cell of node("pet-game-board").children) cell.classList.remove("is-target");
  node("pet-game-start").disabled = claimed;
}

function next() {
  ready = false;
  for (const cell of node("pet-game-board").children) cell.classList.remove("is-target");
  stepTimer = setTimeout(() => {
    if (!run) return;
    ready = true;
    node("pet-game-board").children[run.sequence[index]].classList.add("is-target");
  }, 1100);
}

export function renderGame(world) {
  claimed = world.minigame_claimed;
  if (run) return;
  node("pet-game-start").disabled = world.minigame_claimed;
  node("pet-game-status").textContent = world.minigame_claimed ? "Сегодня награда получена. До завтра!" : "8 светлячков · 30 секунд · 2 монеты";
}

export function initMinigame(receive) {
  node("pet-game-board").replaceChildren(...Array.from({ length: 9 }, (_, cell) => {
    const button = element("button"); button.type = "button"; button.dataset.cell = cell;
    button.setAttribute("aria-label", `Светлячок ${cell + 1}`);
    const icon = element("i"); icon.dataset.lucide = "sparkles"; button.append(icon); return button;
  }));
  refreshIcons();
  node("pet-game-start").onclick = event => runAction(event.currentTarget, async () => {
    stop(); run = await api("/api/pet/game/start", { method: "POST" }); index = 0;
    node("pet-game-start").disabled = true; node("pet-game-status").textContent = "Поймано 0/8";
    endTimer = setTimeout(() => { stop(); node("pet-game-status").textContent = "Время вышло. Попробуем еще?"; }, run.duration * 1000);
    next();
  }).then(() => { node("pet-game-start").disabled = Boolean(run) || claimed; });
  node("pet-game-board").onclick = event => {
    const button = event.target.closest("button");
    if (!run || !ready || Number(button?.dataset.cell) !== run.sequence[index]) return;
    index++; node("pet-game-status").textContent = `Поймано ${index}/8`;
    if (index < 8) return next();
    ready = false; clearTimeout(endTimer);
    runAction(button, async () => {
      let response;
      try { response = await api("/api/pet/game/finish", { method: "POST", body: JSON.stringify({ token: run.token, sequence: run.sequence }) }); }
      finally { stop(); node("pet-game-status").textContent = "Раунд завершен"; }
      receive(response.world); showToast(response.created ? "+2 игровые монеты" : "Награда уже получена");
    });
  };
  node("pet-game-dialog").addEventListener("close", stop);
  document.addEventListener("visibilitychange", () => { if (document.hidden && run) { stop(); node("pet-game-status").textContent = "Раунд остановлен"; } });
}
