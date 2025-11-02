from decimal import Decimal
from pydantic import BaseModel

class OrderCreate(BaseModel):
    user_id: int
    product: str
    quantity: int
    total_price: Decimal

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    id: int
    user_id: int
    product: str
    quantity: int
    total_price: Decimal

    class Config:
        orm_mode = True