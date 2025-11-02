from decimal import Decimal
from pydantic import BaseModel

class OrderCreate(BaseModel):
    """Schema for creating a new order when serving the order create request.
    """
    user_id: int
    product: str
    quantity: int
    total_price: Decimal

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    """Schema for returning order details in responses.
    """
    id: int
    user_id: int
    product: str
    quantity: int
    total_price: Decimal

    class Config:
        orm_mode = True