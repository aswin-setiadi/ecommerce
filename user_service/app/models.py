from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base, ToDictMixIn

class CachedOrder(Base, ToDictMixIn):
    __tablename__ = "cached_orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    # My strategy for atributes that may change is not to cache, call order api instead
    # Should a new query is required that aggregate state/ data from user and order, an API composition approach
    # which sit in its own service is preferred.
    # total_price = Column

class User(Base, ToDictMixIn):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False) # ald validated by pydantic
    name = Column(String, nullable=False)

    # no need for now as we have yet to have requirement on interaction with order
    # orders = relationship("CachedOrder", back_populates="users")

