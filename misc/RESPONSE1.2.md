Perfect 👌 — that’s a very realistic microservice scenario, and a great architecture choice.

So now the design changes from **API + worker** → **two distinct microservices**:

---

## 🧩 **Goal**

We’ll have **two microservices**, both using **FastAPI + SQLAlchemy**, communicating **only via Kafka**.

* **User Service**

  * REST API for user creation and retrieval.
  * Publishes Kafka event `user_created`.
  * Consumes `order_created` events.

* **Order Service**

  * REST API for order creation and retrieval.
  * Publishes Kafka event `order_created`.
  * Consumes `user_created` events.

Both services have **their own database**, showing proper microservice isolation.

---

## ✅ **Architecture Overview**

```
                ┌────────────────────────┐
                │        Kafka           │
                │  (bitnami/kafka)       │
                └──────────┬─────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
┌─────────────────────┐          ┌─────────────────────┐
│     User Service    │          │     Order Service   │
│  FastAPI + SQLA     │          │  FastAPI + SQLA     │
│  DB: users_db       │          │  DB: orders_db      │
│                     │          │                     │
│ Emits: user_created │          │ Emits: order_created│
│ Consumes: order_created│       │ Consumes: user_created│
└─────────────────────┘          └─────────────────────┘
```

---

## 🗂️ Folder Structure

```
ecommerce/
├── user_service/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── kafka_producer.py
│   │   └── kafka_consumer.py
│   ├── Dockerfile
│   └── requirements.txt
├── order_service/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── kafka_producer.py
│   │   └── kafka_consumer.py
│   ├── Dockerfile
│   └── requirements.txt
└── docker-compose.yml
```

---

## 🧠 Core Behavior

| Service | API Endpoint   | Emits Kafka Event | Consumes Event  | DB Action                       |
| ------- | -------------- | ----------------- | --------------- | ------------------------------- |
| User    | `POST /users`  | `user_created`    | `order_created` | Save users; log incoming orders |
| Order   | `POST /orders` | `order_created`   | `user_created`  | Save orders; log incoming users |

The **consumption** side could be as simple as just logging or updating a local “foreign record” table (depending on assignment requirements).

---

## 🧩 Example Implementation

Let’s look at **User Service** first.

---

### `user_service/app/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@user_postgres:5432/users_db")

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
```

---

### `user_service/app/models.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### `user_service/app/schemas.py`

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    class Config:
        orm_mode = True
```

---

### `user_service/app/kafka_producer.py`

```python
import os
import asyncio
import json
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

_producer = None

async def get_producer():
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
        await _producer.start()
    return _producer

async def produce_event(topic: str, payload: dict):
    producer = await get_producer()
    await producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
```

---

### `user_service/app/kafka_consumer.py`

This consumer listens to `order_created` events.

```python
import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

async def consume_order_events():
    consumer = AIOKafkaConsumer(
        "order_created",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="user_service_group",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print(f"[UserService] Received order_created event: {event}")
            # Could update DB or record reference if needed
    finally:
        await consumer.stop()
```

---

### `user_service/app/main.py`

```python
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from .db import SessionLocal, init_db
from .models import User
from .schemas import UserCreate, UserOut
from .kafka_producer import produce_event
from .kafka_consumer import consume_order_events

app = FastAPI(title="User Service")

@app.on_event("startup")
async def startup_event():
    init_db()
    # start consumer in background
    asyncio.create_task(consume_order_events())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users", response_model=UserOut)
async def create_user(user: UserCreate, background_tasks: BackgroundTasks):
    db = next(get_db())
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(400, "User already exists")
    new_user = User(email=user.email, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(produce_event, "user_created", {"user_id": new_user.id, "email": new_user.email})
    return new_user

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

---

Now, the **Order Service** mirrors the same structure, just with its domain swapped.

---

### `order_service/app/models.py`

```python
from sqlalchemy import Column, Integer, Numeric, ForeignKey, DateTime, func
from .db import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Numeric(10,2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### `order_service/app/schemas.py`

```python
from pydantic import BaseModel
from decimal import Decimal

class OrderCreate(BaseModel):
    user_id: int
    amount: Decimal

class OrderOut(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    class Config:
        orm_mode = True
```

---

### `order_service/app/kafka_consumer.py`

Consumes `user_created`:

```python
import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

async def consume_user_events():
    consumer = AIOKafkaConsumer(
        "user_created",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="order_service_group",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print(f"[OrderService] Received user_created event: {event}")
    finally:
        await consumer.stop()
```

---

### `order_service/app/main.py`

```python
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from .db import SessionLocal, init_db
from .models import Order
from .schemas import OrderCreate, OrderOut
from .kafka_producer import produce_event
from .kafka_consumer import consume_user_events

app = FastAPI(title="Order Service")

@app.on_event("startup")
async def startup_event():
    init_db()
    asyncio.create_task(consume_user_events())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/orders", response_model=OrderOut)
async def create_order(order: OrderCreate, background_tasks: BackgroundTasks):
    db = next(get_db())
    new_order = Order(user_id=order.user_id, amount=order.amount)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    background_tasks.add_task(produce_event, "order_created", {"order_id": new_order.id, "user_id": new_order.user_id})
    return new_order

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    db = next(get_db())
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order
```

---

## 🐋 Docker Setup

### `docker-compose.yml`

```yaml
version: "3.8"

services:
  zookeeper:
    image: bitnami/zookeeper:latest
    environment:
      ALLOW_ANONYMOUS_LOGIN: yes
    ports:
      - "2181:2181"

  kafka:
    image: bitnami/kafka:latest
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_LISTENERS=PLAINTEXT://:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - ALLOW_PLAINTEXT_LISTENER=yes
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"

  user_postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: users_db
    ports:
      - "5433:5432"

  order_postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: orders_db
    ports:
      - "5434:5432"

  user_service:
    build:
      context: .
      dockerfile: user_service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@user_postgres:5432/users_db
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - kafka
      - user_postgres
    ports:
      - "8001:8000"

  order_service:
    build:
      context: .
      dockerfile: order_service/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@order_postgres:5432/orders_db
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - kafka
      - order_postgres
    ports:
      - "8002:8000"
```

---

## 🧪 Test Flow

1. Start everything:

   ```bash
   docker-compose up --build
   ```

2. Create a user:

   ```bash
   curl -X POST http://localhost:8001/users \
        -H "Content-Type: application/json" \
        -d '{"email":"alice@example.com", "name":"Alice"}'
   ```

   ➜ You’ll see in **Order Service logs**:

   ```
   [OrderService] Received user_created event: {"user_id":1,"email":"alice@example.com"}
   ```

3. Create an order:

   ```bash
   curl -X POST http://localhost:8002/orders \
        -H "Content-Type: application/json" \
        -d '{"user_id":1,"amount":"59.99"}'
   ```

   ➜ You’ll see in **User Service logs**:

   ```
   [UserService] Received order_created event: {"order_id":1,"user_id":1}
   ```

---

## ⚙️ Key Takeaways (for your report)

* **Decoupled**: Services don’t call each other directly — all communication is event-driven.
* **Independent storage**: Each service has its own Postgres DB.
* **Scalable**: Each consumer group scales independently.
* **Eventually consistent**: Order service only *learns* about new users through Kafka.
* **Patterns**: Demonstrates **event-driven microservices** and **asynchronous integration**.

---

Would you like me to include a **full ready-to-run repo bundle** (all `Dockerfile`s, `requirements.txt`, and small README) so you can copy-paste and run it immediately?
I can generate it in one go.
