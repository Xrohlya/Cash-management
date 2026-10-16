export function revealBudgetSection(id) {
  const section = document.getElementById(id);
  if (!section) return;
  if (section.tagName === "DETAILS") section.open = true;
  for (let parent = section.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === "DETAILS") parent.open = true;
  }
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function initHomeNavigation() {
  document.querySelectorAll("[data-budget-jump]").forEach((button) => {
    button.addEventListener("click", () => revealBudgetSection(button.dataset.budgetJump));
  });
}
