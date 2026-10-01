"""Shared, server-owned game rules. Coins never represent real money."""
from services.pet_appearance import appearance

PETS = {
    "robot": {"name": "Робот", "rooms": ["Мастерская", "Лаборатория", "Космическая станция"]},
    "cat": {"name": "Кот", "rooms": ["Уютная комната", "Дом с садом", "Пентхаус"]},
    "dragon": {"name": "Дракон", "rooms": ["Пещера", "Сокровищница", "Замок"]},
    "penguin": {"name": "Пингвин", "rooms": ["Льдина", "Полярный домик", "Ледяной дворец"]},
    "owl": {"name": "Совёнок", "rooms": ["Гнездо", "Домик на дереве", "Волшебная башня"]},
}
ITEMS = {
    "plant": {"name": "Растение", "cost": 300, "icon": "sprout"},
    "lamp": {"name": "Неоновый светильник", "cost": 750, "icon": "lamp"},
    "books": {"name": "Книги", "cost": 500, "icon": "book-open"},
    "rug": {"name": "Уютный коврик", "cost": 400, "icon": "rectangle-horizontal"},
    "stars": {"name": "Звёздная гирлянда", "cost": 1500, "icon": "sparkles"},
    "trophy": {"name": "Награда", "cost": 4000, "icon": "trophy"},
}
MISSIONS = {
    "feed": {"title": "Кормление", "xp": 10, "coins": 0},
    "visit": {"title": "Заглянуть в свой мир", "xp": 10, "coins": 5},
    "record": {"title": "Вести учёт сегодня", "xp": 15, "coins": 5},
    "save": {"title": "Пополнить накопления", "xp": 20, "coins": 10},
}
STAGES = (0, 3000, 18000)


def item_price(item, level):
    return round(ITEMS[item]["cost"] * 1.5 ** level)


def progression(xp):
    stage = 1 + sum(xp >= threshold for threshold in STAGES[1:])
    floor = STAGES[stage - 1]
    # New chapters continue indefinitely after the final architectural upgrade.
    chapter = max(0, (xp - STAGES[-1]) // 18000) if stage == 3 else 0
    ceiling = STAGES[stage] if stage < len(STAGES) else STAGES[-1] + (chapter + 1) * 18000
    if stage == 3:
        floor = STAGES[-1] + chapter * 18000
    return {"stage": stage, "level": 1 + xp // 50, "next_stage_xp": ceiling,
            **appearance(xp), "chapter": chapter + 1, "size": round(0.65 + min(1, xp / 60000) * 0.4, 3),
            "progress": min(100, round((xp - floor) / (ceiling - floor) * 100))}
