import { element } from "../modules/ui.js?v=20261001-3";
import { seasonalShapes } from "./seasonal-art.js?v=20261002-3";

const shapes = {
  plant: '<path d="M25 30C4 27 4 8 4 8s21 0 21 22M25 32C47 25 47 4 47 4S25 5 25 32" fill="#66dca9"/><path d="M25 17v25" stroke="#94efb8" stroke-width="3"/><path d="M12 35h26l-4 20H16z" fill="#de99b9"/>',
  lamp: '<path d="M25 27v27M9 54h32" stroke="#9ee6ff" stroke-width="4"/><path d="M13 7h24l10 22H3z" fill="#f5d27b"/>',
  books: '<path d="M7 20h9v34H7z" fill="#e998b7"/><path d="M18 12h10v42H18z" fill="#73d8c4"/><path d="m29 19 10-3 9 36-10 3z" fill="#8ac7f4"/>',
  rug: '<ellipse cx="25" cy="32" rx="24" ry="14" fill="#79bdc8"/><ellipse cx="25" cy="32" rx="17" ry="8" fill="none" stroke="#d0f4f4" stroke-width="2"/>',
  stars: '<path d="M1 8Q25 31 49 8" fill="none" stroke="#c1f5fa"/><path d="m10 13 2 5 5 1-4 3 1 5-4-3-5 3 2-5-4-3 5-1zm29 0 2 5 5 1-4 3 1 5-4-3-5 3 2-5-4-3 5-1z" fill="#ffdb7d"/>',
  trophy: '<path d="M15 8h20v18q0 12-10 12T15 26zM25 38v13M13 53h24" fill="#f5cf7b" stroke="#f5cf7b" stroke-width="3"/><path d="M15 12H5v9q0 10 12 10M35 12h10v9q0 10-12 10" fill="none" stroke="#ffd980" stroke-width="3"/>',
};

export function decorations(id) {
  const wrapper = element("span", `room-item room-item-${id}`);
  // Only the fixed local catalog may supply SVG markup.
  wrapper.dataset.item = id;
  wrapper.innerHTML = `<svg viewBox="0 0 50 60" xmlns="http://www.w3.org/2000/svg">${shapes[id] || seasonalShapes[id] || ""}</svg>`;
  return wrapper;
}
