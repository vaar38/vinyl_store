from pydantic import BaseModel, Field

class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=32)

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None = None