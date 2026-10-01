from datetime import date
from pydantic import BaseModel, Field


class Operation(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    description: str = Field(default="", max_length=255)
    request_id: str = Field(min_length=8, max_length=100)


class PeriodSettings(BaseModel):
    financial_day: int = Field(ge=1, le=28)


class RadarSettings(BaseModel):
    target_balance: float = Field(ge=0, le=1_000_000_000)


class SiriExpense(BaseModel):
    text: str = Field(min_length=1, max_length=255)


class GoalSettings(BaseModel):
    target: float = Field(gt=0, le=1_000_000_000)
    target_date: date


class RecurringPayment(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0, le=1_000_000_000)
    kind: str = Field(pattern="^(expense|rent)$")
    day_of_month: int = Field(ge=1, le=28)


class IncomeSource(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    withholding_percent: float = Field(ge=0, le=100)


class ExtraAccount(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AccountTransfer(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    direction: str = Field(pattern="^(to_account|to_main)$")
    request_id: str = Field(min_length=8, max_length=100)


class ExpenseCorrection(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    description: str = Field(min_length=1, max_length=255)


class ResetConfirmation(BaseModel):
    confirmation: str
