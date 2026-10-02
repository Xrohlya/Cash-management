"""Calendar collections, repeat each year without resetting ownership."""
from datetime import date

SEASONS = (
    {"id": "winter", "name": "Зимняя коллекция", "item": "snow", "title": "Ледяной фонарь", "icon": "snowflake", "cost": 1200},
    {"id": "spring", "name": "Весенняя коллекция", "item": "flower", "title": "Цветущий сад", "icon": "flower-2", "cost": 900},
    {"id": "summer", "name": "Летняя коллекция", "item": "sun", "title": "Солнечный талисман", "icon": "sun", "cost": 1200},
    {"id": "autumn", "name": "Осенняя коллекция", "item": "leaf", "title": "Золотая ветвь", "icon": "leaf", "cost": 900},
)


def season(today=None):
    return SEASONS[((today or date.today()).month % 12) // 3]
