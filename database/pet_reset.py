"""User-scoped game reset, independent of financial storage."""
from database import db
from database.db import get_connection
from services.pet_catalog import PETS


GAME_TABLES = (
    "pet_selection", "pet_layout", "pet_album", "pet_minigame",
    "pet_appearance", "pet_item_upgrades", "pet_daily_budget",
    "pet_inventory", "pet_rewards", "pet_world",
)


def clear_game(conn, user_id):
    for table in GAME_TABLES:
        conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))


def change_character(user_id, pet, expected_pet, confirmation):
    if confirmation != "СМЕНИТЬ ПЕРСОНАЖА":
        raise ValueError("Подтвердите сброс игры")
    if pet not in PETS:
        raise ValueError("Неизвестный питомец")
    from database.pets import _profile

    with get_connection() as conn:
        if not db.DATABASE_URL:
            conn.execute("BEGIN IMMEDIATE")
        profile = _profile(conn, user_id, lock=True)
        if profile["pet"] != expected_pet or pet == profile["pet"]:
            raise ValueError("Персонаж уже изменился. Обновите приложение")
        clear_game(conn, user_id)
        conn.execute("INSERT INTO pet_world(user_id,pet) VALUES (?,?)", (user_id, pet))
        conn.execute("INSERT INTO pet_selection(user_id) VALUES (?)", (user_id,))
