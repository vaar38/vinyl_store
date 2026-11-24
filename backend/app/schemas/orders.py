from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=200)
    recipient_phone: str = Field(min_length=1, max_length=32)
    delivery_address: str = Field(min_length=1, max_length=500)
    delivery_comment: str | None = Field(default=None, max_length=1000)
