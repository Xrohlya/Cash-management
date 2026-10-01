"""Isolated game storage. No writes to financial tables."""
from datetime import date

from database import db
from database.db import get_connection
from services.pet_catalog import ITEMS, MISSIONS, PETS, progression


def _profile(conn, user_id, lock=False):
    conn.execute("INSERT INTO pet_world(user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    suffix = " FOR UPDATE" if lock and db.DATABASE_URL else ""
    return dict(conn.execute("SELECT * FROM pet_world WHERE user_id=?" + suffix, (user_id,)).fetchone())


def _missions(conn, user_id, day):
    entries = conn.execute(
        "SELECT kind,amount FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
        (user_id, day + "T00:00:00", day + "T23:59:59.999999"),
    ).fetchall()
    savings = conn.execute("SELECT savings FROM users WHERE user_id=?", (user_id,)).fetchone()
    claimed = {row["mission"] for row in conn.execute("SELECT mission FROM pet_rewards WHERE user_id=? AND day=?", (user_id, day)).fetchall()}
    eligible = {"visit": True, "record": any(row["kind"] in {"income", "expense", "rent", "save", "account_transfer", "account_return"} for row in entries),
                "save": any(row["kind"] == "save" and float(row["amount"]) > 0 for row in entries) and bool(savings and float(savings["savings"]) > 0)}
    return [{"id": key, **value, "eligible": eligible[key], "claimed": key in claimed} for key, value in MISSIONS.items()]


def get_world(user_id):
    with get_connection() as conn:
        profile = _profile(conn, user_id)
        inventory = {row["item"] for row in conn.execute("SELECT item FROM pet_inventory WHERE user_id=?", (user_id,)).fetchall()}
        missions = _missions(conn, user_id, date.today().isoformat())
    pet = PETS[profile["pet"]]
    progress = progression(profile["xp"])
    return {**profile, **progress, "display_name": profile["name"] or pet["name"],
            "room": pet["rooms"][progress["stage"] - 1], "pets": [{"id": key, **value} for key, value in PETS.items()],
            "shop": [{"id": key, **value, "owned": key in inventory} for key, value in ITEMS.items()],
            "inventory": sorted(inventory), "missions": missions}


def update_world(user_id, pet, name, motion):
    if pet not in PETS:
        raise ValueError("Неизвестный питомец")
    with get_connection() as conn:
        _profile(conn, user_id)
        conn.execute("UPDATE pet_world SET pet=?,name=?,motion=? WHERE user_id=?", (pet, name.strip()[:24], int(motion), user_id))


def claim_reward(user_id, mission):
    if mission not in MISSIONS:
        raise ValueError("Неизвестная миссия")
    day = date.today().isoformat()
    with get_connection() as conn:
        if not db.DATABASE_URL:
            conn.execute("BEGIN IMMEDIATE")
        _profile(conn, user_id, lock=True)
        task = next(item for item in _missions(conn, user_id, day) if item["id"] == mission)
        if task["claimed"]:
            return False
        if not task["eligible"]:
            raise ValueError("Условие миссии пока не выполнено")
        inserted = conn.execute("INSERT INTO pet_rewards(user_id,day,mission,xp,coins) VALUES (?,?,?,?,?) ON CONFLICT(user_id,day,mission) DO NOTHING RETURNING mission",
                                (user_id, day, mission, task["xp"], task["coins"])).fetchone()
        if not inserted:
            return False
        conn.execute("UPDATE pet_world SET xp=xp+?,coins=coins+? WHERE user_id=?", (task["xp"], task["coins"], user_id))
    return True


def buy_item(user_id, item):
    if item not in ITEMS:
        raise ValueError("Неизвестное украшение")
    with get_connection() as conn:
        if not db.DATABASE_URL:
            conn.execute("BEGIN IMMEDIATE")
        profile = _profile(conn, user_id, lock=True)
        if conn.execute("SELECT item FROM pet_inventory WHERE user_id=? AND item=?", (user_id, item)).fetchone():
            return False
        if profile["coins"] < ITEMS[item]["cost"]:
            raise ValueError("Пока недостаточно игровых монет")
        conn.execute("INSERT INTO pet_inventory(user_id,item) VALUES (?,?)", (user_id, item))
        conn.execute("UPDATE pet_world SET coins=coins-? WHERE user_id=?", (ITEMS[item]["cost"], user_id))
    return True
