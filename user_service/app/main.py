import asyncio
from contextlib import asynccontextmanager
import logging
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException

from .db import init_db, SessionLocal
from .kafka_consumer import consume_order_events
from .kafka_producer import produce_event
from .models import User
from .schemas import UserCreate, UserOut

LOG_PATH= os.getenv('LOG_PATH')
os.makedirs(LOG_PATH, exist_ok=True)
logging.basicConfig(
    filename=f'{LOG_PATH}/user_service.log',
    level=logging.INFO,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger= logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.consumer_task=asyncio.create_task(consume_order_events())
    yield
    app.consumer_task.cancel()

app= FastAPI(lifespan=lifespan,title="E-commerce API with Kafka Integration")

def get_db():
    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users", response_model= UserOut, status_code=201)
async def create_user(user: UserCreate, background_task: BackgroundTasks):
    db= next(get_db())
    db_user= db.query(User).filter(User.email== user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user= User(**user.model_dump())
    db.add(new_user)
    db.commit()
    logger.info(f"Created new user: {new_user.to_dict()}")
    # By default session.commit() treat all obj in the session as "expired"
    # through default behavior of expire_on_commit=True.
    # Also this session will be garbage collected after the function return
    # db.refresh(new_user)
    background_task.add_task(produce_event, "user_created", new_user.to_dict())
    return new_user

@app.get("/users/{user_id}", response_model= UserOut)
def get_user(user_id: int):
    db= next(get_db())
    user= db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

