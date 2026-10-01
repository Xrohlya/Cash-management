"""Shared, server-owned game rules. Coins never represent real money."""

PETS = {
    "robot": {"name": "Робот", "rooms": ["Мастерская", "Лаборатория", "Космическая станция"]},
    "cat": {"name": "Кот", "rooms": ["Уютная комната", "Дом с садом", "Пентхаус"]},
    "dragon": {"name": "Дракон", "rooms": ["Пещера", "Сокровищница", "Замок"]},
    "penguin": {"name": "Пингвин", "rooms": ["Льдина", "Полярный домик", "Ледяной дворец"]},
    "owl": {"name": "Совёнок", "rooms": ["Гнездо", "Домик на дереве", "Волшебная башня"]},
}
ITEMS = {
    "plant": {"name": "Растение", "cost": 10, "icon": "sprout"},
    "lamp": {"name": "Неоновый светильник", "cost": 15, "icon": "lamp"},
    "books": {"name": "Книги", "cost": 12, "icon": "book-open"},
    "rug": {"name": "Уютный коврик", "cost": 10, "icon": "rectangle-horizontal"},
    "stars": {"name": "Звёздная гирлянда", "cost": 20, "icon": "sparkles"},
    "trophy": {"name": "Награда", "cost": 30, "icon": "trophy"},
}
MISSIONS = {
    "feed": {"title": "Кормление", "xp": 10, "coins": 0},
    "visit": {"title": "Заглянуть в свой мир", "xp": 10, "coins": 5},
    "record": {"title": "Вести учёт сегодня", "xp": 15, "coins": 5},
    "save": {"title": "Пополнить накопления", "xp": 20, "coins": 10},
}
STAGES = (0, 100, 250)


def progression(xp):
    stage = 1 + sum(xp >= threshold for threshold in STAGES[1:])
    floor = STAGES[stage - 1]
    ceiling = STAGES[stage] if stage < len(STAGES) else None
    return {"stage": stage, "level": 1 + xp // 50, "next_stage_xp": ceiling,
            "progress": min(100, round((xp - floor) / (ceiling - floor) * 100)) if ceiling else 100}
