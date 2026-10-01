import { showToast } from "./core.js?v=20261001-2";

export function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

export function iconButton(icon, title, className = "mini-icon") {
  const button = element("button", className);
  button.type = "button";
  button.title = title;
  button.setAttribute("aria-label", title);
  const image = element("i");
  image.dataset.lucide = icon;
  image.setAttribute("aria-hidden", "true");
  button.append(image);
  return button;
}

export function refreshIcons() {
  window.lucide?.createIcons();
}

export function dateLabel(value) {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

export async function runAction(button, work) {
  if (button?.disabled) return;
  if (button) button.disabled = true;
  try {
    await work();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

export function bindForm(id, work) {
  const form = document.getElementById(id);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runAction(event.submitter || form.querySelector('[type="submit"]'), () => work(form));
  });
}

export function requestConfirmation(message) {
  const dialog = document.getElementById("action-confirm-dialog");
  if (dialog.open) return Promise.resolve(false);
  const form = document.getElementById("action-confirm-form");
  const cancel = document.getElementById("cancel-action-confirm");
  document.getElementById("action-confirm-text").textContent = message;
  dialog.returnValue = "";
  return new Promise((resolve) => {
    const submit = (event) => { event.preventDefault(); dialog.close("confirmed"); };
    const dismiss = () => dialog.close("");
    form.addEventListener("submit", submit);
    cancel.addEventListener("click", dismiss);
    dialog.addEventListener("close", () => {
      form.removeEventListener("submit", submit);
      cancel.removeEventListener("click", dismiss);
      resolve(dialog.returnValue === "confirmed");
    }, { once: true });
    dialog.showModal();
  });
}
