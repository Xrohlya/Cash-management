import { element } from "../modules/ui.js?v=20261001-3";

const filters = {
  original: "none",
  blue: "sepia(0.7) saturate(1.6) hue-rotate(165deg)",
  mint: "sepia(0.7) saturate(1.6) hue-rotate(95deg)",
  violet: "sepia(0.7) saturate(1.6) hue-rotate(215deg)",
  rose: "sepia(0.7) saturate(1.6) hue-rotate(285deg)",
  gold: "sepia(0.7) saturate(1.6) hue-rotate(0deg)",
};

export function previewColor(color) {
  document.getElementById("pet-model-frame").style.filter = filters[color] || "none";
  document.getElementById("pet-color-preview").style.filter = filters[color] || "none";
}

export function selectedColor() {
  return document.querySelector('input[name="pet-color"]:checked')?.value || "original";
}

export function renderModel(frame, pet, stage) {
  const image = frame.querySelector("img");
  image.src = `/static/pets/images/${pet}-ages.png`;
  image.style.left = `${-((stage - 1) % 3) * 100}%`;
  image.style.top = `${-Math.floor((stage - 1) / 3) * 100}%`;
}

export function renderAppearance(world) {
  const frame = document.getElementById("pet-model-frame");
  frame.style.transform = `scale(${world.size})`;
  renderModel(frame, world.pet, world.age_stage);
  renderModel(document.getElementById("pet-color-preview"), world.pet, world.age_stage);
  document.getElementById("pet-colors").replaceChildren(...world.colors.map((color) => {
    const label = element("label", "pet-color-swatch");
    label.title = color.name;
    label.style.setProperty("--swatch", color.hex);
    const radio = element("input");
    radio.type = "radio";
    radio.name = "pet-color";
    radio.value = color.id;
    radio.checked = color.id === world.color;
    radio.setAttribute("aria-label", color.name);
    label.append(radio, element("span"));
    return label;
  }));
  previewColor(world.color);
  const next = document.getElementById("pet-next-age");
  next.textContent = world.next_age_xp ? `Следующий возраст: ${world.next_age_xp} опыта` : "Легендарный облик открыт";
  document.getElementById("pet-age-progress").value = world.age_progress;
}
