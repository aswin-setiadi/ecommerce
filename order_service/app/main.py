import asyncio
from contextlib import asynccontextmanager
import logging
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException

from .db import init_db, SessionLocal
from .models import CachedUser, Order
from .kafka_consumer import consume_user_events
from .kafka_producer import produce_event
from .schemas import OrderCreate, OrderOut

os.makedirs('/var/log/app', exist_ok=True)
logging.basicConfig(
    filename='/var/log/app/order_service.log',
    level=logging.INFO,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger= logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.consumer_task=asyncio.create_task(consume_user_events())
    yield
    app.consumer_task.cancel()

app= FastAPI(lifespan=lifespan,title="E-commerce API with Kafka Integration")

def get_db():
    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/orders", response_model= OrderOut, status_code=201)
async def create_order(order: OrderCreate, background_tasks: BackgroundTasks):
    """Create a new order after verifying the user exists.

    :param order: OrderCreate object containing order details
    :type order: OrderCreate
    :param background_tasks: BackgroundTasks for scheduling Kafka event production
    :type background_tasks: BackgroundTasks
    :raises HTTPException: Raises 404 if user not found
    :return: the newly created Order object
    :rtype: Order
    """
    db= next(get_db())
    user= db.query(CachedUser).get(order.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_order= Order(**order.model_dump())
    db.add(new_order)
    db.commit()
    logger.info(f"Created new order: {new_order.to_dict()}")
    # By default session.commit() treat all obj in the session as "expired"
    # through default behavior of expire_on_commit=True.
    # Also this session will be garbage collected after the function return
    # db.refresh(new_order)
    background_tasks.add_task(produce_event, "order_created", new_order.to_dict())
    return new_order

@app.get("/orders/{order_id}", response_model= OrderOut)
def get_order(order_id: int):
    db= next(get_db())
    order= db.query(Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
