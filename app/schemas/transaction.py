from datetime import date as DateType
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class TransactionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    type: Literal["income", "expense"]

    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    category: str = Field(min_length=1, max_length=50)
    date: DateType
    description: str | None = Field(default=None, max_length=500)


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    type: Literal["income", "expense"] | None = None

    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    date: DateType | None = None

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")

        required_fields = {"type", "amount", "category", "date"}

        for field in required_fields & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: Literal["income", "expense"]
    amount: Decimal
    category: str
    date: DateType
    description: str | None
    currency: Literal["EUR"] = "EUR"

class TransactionSummary(BaseModel):
    income: Decimal
    expense: Decimal
    balance: Decimal
    currency: Literal["EUR"] = "EUR"