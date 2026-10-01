"""Cosmetic evolution independent of room upgrades and financial data."""

AGES = ((0, "Малыш"), (1000, "Подросток"), (6000, "Молодой"),
        (20000, "Взрослый"), (60000, "Легенда"))
COLORS = {
    "original": {"name": "Оригинальный", "hex": "#c1ced9"},
    "blue": {"name": "Синий", "hex": "#49a7ff"},
    "mint": {"name": "Мятный", "hex": "#65e5bd"},
    "violet": {"name": "Фиолетовый", "hex": "#b78cff"},
    "rose": {"name": "Розовый", "hex": "#ff8eac"},
    "gold": {"name": "Золотой", "hex": "#efcd72"},
}


def appearance(xp):
    index = sum(xp >= threshold for threshold, _ in AGES[1:])
    next_xp = AGES[index + 1][0] if index < len(AGES) - 1 else None
    return {"age_stage": index + 1, "age": AGES[index][1], "next_age_xp": next_xp,
            "age_progress": min(100, round((xp - AGES[index][0]) / (next_xp - AGES[index][0]) * 100)) if next_xp else 100}
