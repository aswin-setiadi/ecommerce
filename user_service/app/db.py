import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL= os.getenv("DATABASE_URL")

engine= create_engine(DB_URL, pool_pre_ping=True)
SessionLocal= sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base= declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

class ToDictMixIn:
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}