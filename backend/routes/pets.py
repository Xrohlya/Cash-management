from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import current_user
from database.pets import buy_item, claim_reward, get_world, update_world
from database.pet_feeding import remember_daily_limit
from backend.payloads import state

router = APIRouter(prefix="/api/pet", tags=["Pet world"])


class WorldSettings(BaseModel):
    pet: str = Field(max_length=16)
    name: str = Field(default="", max_length=24)
    motion: bool = True


class GameAction(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    expected_level: int = Field(default=0, ge=0, le=3)


def action(function, *args):
    try:
        return function(*args)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("")
def world(user_id: int = Depends(current_user)):
    current = state(user_id)
    remember_daily_limit(user_id, current["daily_limit"], current["today"], current["days_left"])
    return get_world(user_id)


@router.post("/settings")
def settings(data: WorldSettings, user_id: int = Depends(current_user)):
    action(update_world, user_id, data.pet, data.name, data.motion)
    return get_world(user_id)


@router.post("/claim")
def claim(data: GameAction, user_id: int = Depends(current_user)):
    created = action(claim_reward, user_id, data.id)
    return {"created": created, "world": get_world(user_id)}


@router.post("/buy")
def buy(data: GameAction, user_id: int = Depends(current_user)):
    created = action(buy_item, user_id, data.id, data.expected_level)
    return {"created": created, "world": get_world(user_id)}
