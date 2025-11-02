
from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.orm import relationship
from .db import Base, ToDictMixIn

class CachedUser(Base, ToDictMixIn):
    __tablename__ = "cached_users"
    id = Column(Integer, primary_key=True, index=True)
    # I think no need for now cause this is just cache to validate id
    # email = Column(String, unique=True, index=True, nullable=False)
    # name = Column(String, nullable=False)
    # orders = relationship("Order", back_populates="user")


class Order(Base, ToDictMixIn):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10,2), nullable=False)

    # no need in microservice approach, also user_id ald representative
    # user = relationship("User", back_populates="orders")
