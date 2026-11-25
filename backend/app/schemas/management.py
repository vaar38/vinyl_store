from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ArtistData(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    biography: str | None = None
    image_url: str | None = None


class GenreData(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class RecordData(BaseModel):
    artist_id: int = Field(gt=0)
    genre_id: int = Field(gt=0)
    album: str = Field(min_length=1, max_length=300)
    description: str | None = None
    cover_url: str | None = None
    release_year: int | None = Field(default=None, ge=1900, le=2100)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    available_stock: int = Field(ge=0)
    is_active: bool = True

    @field_validator("price")
    @classmethod
    def finite_price(cls, value):
        if not value.is_finite():
            raise ValueError("Цена должна быть конечным числом")
        return value


class RecordUpdate(RecordData):
    expected_updated_at: datetime


class OrderStatusUpdate(BaseModel):
    status: Literal["assembling", "ready", "shipped", "delivered"]
