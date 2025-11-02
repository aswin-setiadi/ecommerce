Nice — that’s a clear assignment. Below I’ll give:

1. a recommended architecture (the “best” decision with trade-offs)
2. concrete implementation plan and directory layout
3. runnable example code for: SQLAlchemy models, FastAPI microservice (API), a simple Kafka producer, and a separate Kafka consumer worker that also interacts with the DB
4. Dockerfile(s) and `docker-compose.yml` that wire Postgres, Zookeeper, Kafka, API and worker together
5. notes on reliability, ordering, idempotency, and how to test

I won’t ask follow-ups — I’ll assume the API should support create/retrieve for **users** and **orders**, and that Kafka must be used for communication *between microservices* (not merely internal logging).

---

# 1) Recommended architecture (single best choice + rationale)

**Recommendation (Best for an assignment + production-feel):**
Use a small *event-driven microservice* pattern with **two services**:

* **api**: FastAPI service. Handles HTTP requests to create / retrieve users and create orders. Writes authoritative user and order rows to the Postgres DB **synchronously** for immediate read-after-write behavior. When an important domain event happens (e.g. `order_created`, `user_created`), the API **produces** an event to Kafka.
* **worker (order processor)**: Another microservice that **consumes** Kafka events (e.g. `order_created`) to perform asynchronous tasks (e.g. send confirmations, run further processing, call external systems). The worker may also update DB with processed flags, or call other microservices.

**Why this choice?**

* Demonstrates Kafka for inter-service communication (API → Kafka → worker).
* Keeps reads consistent (API writes DB so GET returns data immediately).
* Worker can scale independently and emulate long-running tasks.
* Achieves loose coupling and eventual consistency — typical real-world pattern.

**Important trade-offs**

* Simpler alternative: API writes DB and **also** writes to another DB directly; **but** that wouldn't use Kafka.
* Fully asynchronous (API only produces event and worker inserts to DB) would be more complex (you must offer clients a way to check order status while eventual write completes). For assignment clarity we do synchronous write + event produce.

**Reliability choices**

* Use **at-least-once** semantics for Kafka (typical). Make consumers idempotent (use order ID/unique constraints).
* Producer should handle transient failures (retry + backoff).
* Use DB transactions to ensure API only produces event after DB commit (or use outbox pattern for stronger guarantees — I’ll mention it).

---

# 2) Project layout

```
ecommerce/
├─ api/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ db.py
│  │  └─ kafka_producer.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ worker/
│  ├─ consumer.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ docker-compose.yml
└─ README.md
```

---

# 3) Concrete code (minimal, practical)

Below are ready-to-run snippets. They’re synchronous SQLAlchemy (classic ORM) for clarity and FastAPI. The Kafka client I’ll use is **aiokafka** (async), which fits nicely with FastAPI background tasks.

> Note: In code we use `POSTGRES_HOST=postgres`, `KAFKA_BOOTSTRAP_SERVERS=kafka:9092` — those host names are created by `docker-compose`.

### `api/app/db.py`

```python
# api/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/ecommerce")

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
```

### `api/app/models.py`

```python
# api/app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Boolean, func
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10,2), nullable=False)
    status = Column(String, default="created")  # created, processed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False)

    user = relationship("User", back_populates="orders")
```

### `api/app/schemas.py`

```python
# api/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal

class UserCreate(BaseModel):
    email: EmailStr
    name: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    user_id: int
    amount: Decimal

class OrderOut(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    status: str
    class Config:
        orm_mode = True
```

### `api/app/kafka_producer.py`

```python
# api/app/kafka_producer.py
import os
import asyncio
from aiokafka import AIOKafkaProducer
import json

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

producer = None

async def get_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
        await producer.start()
    return producer

async def produce_event(topic: str, event: dict):
    p = await get_producer()
    await p.send_and_wait(topic, json.dumps(event).encode("utf-8"))
```

### `api/app/main.py`

```python
# api/app/main.py
import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from decimal import Decimal

from .db import SessionLocal, init_db
from .models import User, Order
from .schemas import UserCreate, UserOut, OrderCreate, OrderOut
from .kafka_producer import produce_event

app = FastAPI(title="ecommerce-api")

@app.on_event("startup")
async def startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create user
@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(u: UserCreate, background_tasks: BackgroundTasks):
    db = next(get_db())
    existing = db.query(User).filter(User.email == u.email).first()
    if existing:
        raise HTTPException(400, "email already exists")
    user = User(email=u.email, name=u.name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # produce event in background (non-blocking)
    background_tasks.add_task(produce_event, "user_created", {"user_id": user.id, "email": user.email})
    return user

# Get user
@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return user

# Create order
@app.post("/orders", response_model=OrderOut, status_code=201)
async def create_order(o: OrderCreate, background_tasks: BackgroundTasks):
    db = next(get_db())
    user = db.query(User).get(o.user_id)
    if not user:
        raise HTTPException(404, "user not found")
    order = Order(user_id=o.user_id, amount=o.amount, status="created")
    db.add(order)
    db.commit()
    db.refresh(order)

    # produce order_created event
    background_tasks.add_task(produce_event, "order_created", {"order_id": order.id, "user_id": order.user_id, "amount": str(order.amount)})
    return order

# Get order
@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    db = next(get_db())
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    return order
```

> Notes:
>
> * I used `background_tasks` to produce events asynchronously so request latency isn't blocked waiting for the Kafka roundtrip.
> * For stronger guarantees (no event loss), use the **outbox pattern**: write event to an `outbox` table in same DB transaction and have a separate process publish outbox rows to Kafka.

---

### `worker/consumer.py` (simple consumer + idempotent processing)

```python
# worker/consumer.py
import asyncio
import os
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.models import Base, Order  # if you package models; otherwise duplicate models in worker
from api.app.db import DB_URL if False else None

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/ecommerce")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

TOPIC = "order_created"

async def handle_order_created(event: dict):
    order_id = int(event["order_id"])
    session = SessionLocal()
    try:
        order = session.query(Order).get(order_id)
        if not order:
            print(f"Order {order_id} not found in DB; skipping")
            return
        # idempotency: if already processed, skip
        if order.processed:
            print(f"Order {order_id} already processed; skipping")
            return

        # simulate processing (send email, charge card, etc)
        # ... do work ...

        # mark as processed
        order.status = "processed"
        order.processed = True
        session.add(order)
        session.commit()
        print(f"Processed order {order_id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

async def consume():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="order_workers",
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print("Got event:", event)
            # handle with retry/backoff in prod
            await handle_order_created(event)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())
```

> For the worker, you can either import the same `models` from API package (if packaged), or duplicate the minimal model definitions. The worker marks `processed=True` to make processing idempotent.

---

# 4) Docker

### `api/Dockerfile`

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app/ ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

`api/requirements.txt`

```
fastapi
uvicorn[standard]
sqlalchemy>=1.4
psycopg2-binary
aiokafka
pydantic
```

### `worker/Dockerfile`

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/ ./worker
# If worker imports models from api package, copy them too (or pip install package)
COPY api/app/ ./api/app
CMD ["python", "worker/consumer.py"]
```

`worker/requirements.txt`

```
aiokafka
sqlalchemy>=1.4
psycopg2-binary
```

### `docker-compose.yml`

```yaml
version: "3.8"
services:
  zookeeper:
    image: bitnami/zookeeper:latest
    environment:
      - ALLOW_ANONYMOUS_LOGIN=yes
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

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ecommerce
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]

  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/ecommerce
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - postgres
      - kafka
    ports:
      - "8000:8000"

  worker:
    build:
      context: .
      dockerfile: worker/Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/ecommerce
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - postgres
      - kafka
```

Run:

```
docker-compose up --build
```

---

# 5) Testing locally (quick commands)

Create a user:

```
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d '{"email":"alice@example.com","name":"Alice"}'
```

Create an order:

```
curl -X POST http://localhost:8000/orders -H "Content-Type: application/json" -d '{"user_id":1,"amount":"49.99"}'
```

Then check `/orders/1` or watch the `worker` logs to see processing.

---

# 6) Notes on robustness, production considerations & grading pointers

* **Atomicity between DB write and event publish**: background task producing after commit is okay for assignment, but could lose event if API crashes after DB commit but before produce. For **exactly-once/outbox** guarantees use Outbox pattern (write DB + outbox row in same DB tx; separate publisher reliably moves outbox to Kafka).
* **Idempotence**: Consumer must be idempotent. Use unique constraints & processed flags. Use `order_id` primary key to avoid duplicates.
* **Retries and DLQs**: On repeated failures consumer should move the event to a dead-letter queue (topic) after N retries.
* **Schema evolution**: use JSON schema or Avro for events in larger systems. For this assignment, JSON is fine.
* **Consumer group scaling**: use `group_id` to scale horizontally; careful with ordering across partitions (if you need per-user order ordering, produce with `key=user_id` so partitioning keeps per-user ordering).
* **Testing**: use integration tests with docker-compose, and unit tests mocking the Kafka producer.
* **Observability**: logs, metrics and health endpoints matter — add them if you have time.

---

# 7) Alternatives briefly (when to choose them)

* **Single service + Kafka used only for notifications**: simpler. Use if assignment only requires Kafka used anywhere.
* **API flows only via Kafka (producer only) and worker writes DB**: true event-sourced approach; but requires client to poll/subscribe for order completion or store order status externally. Use if you want to demonstrate full event-driven system.

---

# 8) Deliverables I can drop next (if you want them right now)

I already gave the runnable pieces above, but if you want I can immediately produce one of these (pick one; I’ll include the file content ready to paste):

* Full `docker-compose.yml` + complete `api/app` files in one copy-pasteable bundle.
* A short Alembic migration and instructions for schema migrations.
* A small pytest suite that spins up services with `pytest-docker-compose` (or simple unit tests mocking Kafka).
* A simple README with commands and checklist for grading.

Tell me which of those you want **right now** and I’ll produce it exactly (I’ll include full files).
