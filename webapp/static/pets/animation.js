const phrases = ["Рад тебя видеть!", "Мы отличная команда!", "Маленький шаг — тоже шаг.", "У нас уютно!"];
let stopReaction;

export function reactToPet() {
  const stage = document.getElementById("pet-stage");
  const reaction = document.getElementById("pet-reaction");
  clearTimeout(stopReaction);
  stage.classList.remove("is-playing");
  requestAnimationFrame(() => stage.classList.add("is-playing"));
  reaction.textContent = phrases[Math.floor(Math.random() * phrases.length)];
  stopReaction = setTimeout(() => { stage.classList.remove("is-playing"); reaction.textContent = ""; }, 1800);
}
