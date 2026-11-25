from pydantic import BaseModel

from decimal import Decimal


class RecordsResponse(BaseModel):
    id: int
    album: str
    artist: str
    price: Decimal
    available_stock: int
    cover_url: str | None = None


class RecordDetailResponse(RecordsResponse):
    description: str | None = None
    release_year: int | None = None
    genre: str
