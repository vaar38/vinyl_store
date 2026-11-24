from pydantic import BaseModel, Field

class CartItemCreate(BaseModel):
    record_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)
