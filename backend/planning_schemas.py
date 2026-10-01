from datetime import date
from pydantic import BaseModel, Field


class PlannedIncome(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    amount: float = Field(ge=0.01, le=1_000_000_000)
    due_date: date
    source_id: int | None = Field(default=None, gt=0)


class CategoryLimit(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: float = Field(ge=0.01, le=1_000_000_000)


class CategoryName(BaseModel):
    category: str = Field(min_length=1, max_length=80)


class UndoOperation(BaseModel):
    transaction_id: int = Field(gt=0)
    confirmed: bool = False
