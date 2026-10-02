"""Furniture, memories and a bounded daily game. No financial writes."""
import hashlib
import json
import secrets
import time
from datetime import date

from database import db
from database.db import get_connection
from services.pet_appearance import AGES
from services.pet_seasons import season


def _lock(conn, user_id):
    if not db.DATABASE_URL:
        conn.execute("BEGIN IMMEDIATE")
    from database.pets import _profile
    return _profile(conn, user_id, lock=True)


def life(conn, user_id, xp):
    today = date.today().isoformat()
    album = [dict(row) for row in conn.execute("SELECT event,title,recorded_at FROM pet_album WHERE user_id=? ORDER BY recorded_at,event", (user_id,)).fetchall()]
    existing = {row["event"] for row in album}
    for index, (threshold, name) in enumerate(AGES, 1):
        if xp >= threshold and f"age:{index}" not in existing:
            conn.execute("INSERT INTO pet_album(user_id,event,title,recorded_at) VALUES (?,?,?,?) ON CONFLICT(user_id,event) DO NOTHING",
                         (user_id, f"age:{index}", name, today))
            album.append({"event": f"age:{index}", "title": name, "recorded_at": today})
    goal = conn.execute("SELECT g.target,g.target_date,u.savings FROM goals g JOIN users u ON u.user_id=g.user_id WHERE g.user_id=?", (user_id,)).fetchone()
    if goal and float(goal["target"]) > 0 and float(goal["savings"]) >= float(goal["target"]):
        key = hashlib.sha256(f'{goal["target"]}:{goal["target_date"]}'.encode()).hexdigest()[:24]
        if f"goal:{key}" not in existing:
            title = f'Цель достигнута: {float(goal["target"]):g} ₽'
            conn.execute("INSERT INTO pet_album(user_id,event,title,recorded_at) VALUES (?,?,?,?) ON CONFLICT(user_id,event) DO NOTHING", (user_id, f"goal:{key}", title, today))
            album.append({"event": f"goal:{key}", "title": title, "recorded_at": today})
    album.sort(key=lambda row: (row["recorded_at"], row["event"]))
    claimed = conn.execute("SELECT mission FROM pet_rewards WHERE user_id=? AND day=? AND mission='minigame'", (user_id, today)).fetchone()
    return {"layout": {row["item"]: {"x": row["x"], "y": row["y"]} for row in conn.execute("SELECT item,x,y FROM pet_layout WHERE user_id=?", (user_id,)).fetchall()},
            "album": album, "season": season(), "minigame_claimed": bool(claimed),
            "goal_badge": any(row["event"].startswith("goal:") for row in album)}


def save_layout(user_id, positions):
    with get_connection() as conn:
        _lock(conn, user_id)
        owned = {row["item"] for row in conn.execute("SELECT item FROM pet_inventory WHERE user_id=?", (user_id,)).fetchall()}
        if set(positions) - owned:
            raise ValueError("Можно переставлять только купленные предметы")
        for item, position in positions.items():
            x, y = float(position["x"]), float(position["y"])
            if not 0 <= x <= 85 or not 5 <= y <= 75:
                raise ValueError("Предмет должен оставаться внутри комнаты")
            conn.execute("INSERT INTO pet_layout(user_id,item,x,y) VALUES (?,?,?,?) ON CONFLICT(user_id,item) DO UPDATE SET x=excluded.x,y=excluded.y", (user_id, item, x, y))


def start_game(user_id):
    today = date.today().isoformat()
    with get_connection() as conn:
        _lock(conn, user_id)
        if conn.execute("SELECT mission FROM pet_rewards WHERE user_id=? AND day=? AND mission='minigame'", (user_id, today)).fetchone():
            raise ValueError("Сегодня награда уже получена")
        sequence = [secrets.randbelow(9)]
        for _ in range(7):
            choices = [i for i in range(9) if i != sequence[-1]]
            sequence.append(secrets.choice(choices))
        token = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO pet_minigame(user_id,day,token,sequence,started) VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET day=excluded.day,token=excluded.token,sequence=excluded.sequence,started=excluded.started", (user_id, today, token, json.dumps(sequence), time.time()))
    return {"token": token, "sequence": sequence, "duration": 30, "reward": 2}


def finish_game(user_id, token, sequence):
    today = date.today().isoformat()
    with get_connection() as conn:
        _lock(conn, user_id)
        run = conn.execute("SELECT * FROM pet_minigame WHERE user_id=?", (user_id,)).fetchone()
        if not run or run["token"] != token or run["day"] != today or json.loads(run["sequence"]) != sequence or not 8 <= time.time() - run["started"] <= 120:
            raise ValueError("Раунд завершен или результат не подтвержден")
        added = conn.execute("INSERT INTO pet_rewards(user_id,day,mission,xp,coins) VALUES (?,?,'minigame',0,2) ON CONFLICT(user_id,day,mission) DO NOTHING RETURNING mission", (user_id, today)).fetchone()
        if added:
            conn.execute("UPDATE pet_world SET coins=coins+2 WHERE user_id=?", (user_id,))
    return bool(added)
