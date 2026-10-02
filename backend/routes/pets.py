from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated

from backend.auth import current_user
from database.pets import buy_item, claim_reward, get_world, update_world
from database.pet_feeding import remember_daily_limit
from backend.payloads import state
from database.pet_life import save_layout, start_game, finish_game
from database.pet_reset import change_character

router = APIRouter(prefix="/api/pet", tags=["Pet world"])


class WorldSettings(BaseModel):
    pet: str = Field(max_length=16)
    name: str = Field(default="", max_length=24)
    motion: bool = True
    color: str | None = Field(default=None, max_length=16)


class GameAction(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    expected_level: int = Field(default=0, ge=0, le=3)


class CharacterChange(BaseModel):
    pet: str = Field(max_length=16)
    expected_pet: str = Field(max_length=16)
    confirmation: str = Field(max_length=32)


class Position(BaseModel):
    x: float = Field(ge=0, le=85, allow_inf_nan=False)
    y: float = Field(ge=5, le=75, allow_inf_nan=False)


class Layout(BaseModel):
    positions: dict[str, Position] = Field(max_length=20)


class Result(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    sequence: list[Annotated[int, Field(ge=0, le=8)]] = Field(min_length=8, max_length=8)


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
    action(update_world, user_id, data.pet, data.name, data.motion, data.color)
    return get_world(user_id)


@router.post("/claim")
def claim(data: GameAction, user_id: int = Depends(current_user)):
    created = action(claim_reward, user_id, data.id)
    return {"created": created, "world": get_world(user_id)}


@router.post("/character")
def character(data: CharacterChange, user_id: int = Depends(current_user)):
    action(change_character, user_id, data.pet, data.expected_pet, data.confirmation)
    return get_world(user_id)


@router.post("/buy")
def buy(data: GameAction, user_id: int = Depends(current_user)):
    created = action(buy_item, user_id, data.id, data.expected_level)
    return {"created": created, "world": get_world(user_id)}


@router.post("/layout")
def layout(data: Layout, user_id: int = Depends(current_user)):
    action(save_layout, user_id, {key: value.model_dump() for key, value in data.positions.items()})
    return get_world(user_id)


@router.post("/game/start")
def game_start(user_id: int = Depends(current_user)):
    return action(start_game, user_id)


@router.post("/game/finish")
def game_finish(data: Result, user_id: int = Depends(current_user)):
    created = action(finish_game, user_id, data.token, data.sequence)
    return {"created": created, "world": get_world(user_id)}
