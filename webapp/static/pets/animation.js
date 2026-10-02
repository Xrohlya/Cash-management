const phrases = ["Рад тебя видеть!", "Мы отличная команда!", "Маленький шаг — тоже шаг.", "У нас уютно!"];
const personality = { robot: ["Проверяю звездные карты!", "Новые открытия впереди."], cat: ["Здесь мое любимое место.", "Можно еще немного погладить."], dragon: ["Сокровища под защитой!", "Готов к приключениям."], penguin: ["С тобой теплее!", "Давай поиграем."], owl: ["Нашел интересную книгу.", "Люблю тихие вечера."] };
let stopReaction;

export function reactToPet() {
  const stage = document.getElementById("pet-stage");
  const reaction = document.getElementById("pet-reaction");
  clearTimeout(stopReaction);
  stage.classList.remove("is-playing");
  requestAnimationFrame(() => stage.classList.add("is-playing"));
  const choices = stage.dataset.activity === "sleep" ? ["Сонный привет…", "Еще пять минуточек…"] : [...phrases, ...(personality[stage.dataset.pet] || [])];
  reaction.textContent = choices[Math.floor(Math.random() * choices.length)];
  stopReaction = setTimeout(() => { stage.classList.remove("is-playing"); reaction.textContent = ""; }, 1800);
}
