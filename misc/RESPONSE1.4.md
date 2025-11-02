Excellent — this is the **classic “bi-directional event flow”** setup between microservices.
Let’s make it concrete, clean, and *assignments-grade strong*.

You already have:

* **User Service** (creates users, publishes `user_created`).
* **Order Service** (creates orders, publishes `order_created`).

Now your requirement is:

> The **User Service** must also **consume `order_created` events** from Kafka.

Let’s go step-by-step on *how to architect this cleanly*, *how to code it*, and *how to run it with FastAPI + aiokafka + Docker*.

---

## 🧩 1. High-level Design

### Services:

| Service           | API       | Emits           | Consumes        | DB          |
| ----------------- | --------- | --------------- | --------------- | ----------- |
| **User Service**  | `/users`  | `user_created`  | `order_created` | `users_db`  |
| **Order Service** | `/orders` | `order_created` | `user_created`  | `orders_db` |

Each service:

* Has **FastAPI** for REST API.
* Runs **an async Kafka consumer** in the background (inside the same container).
* Writes to its own database only.
* Reacts to the other service’s events (log, cache, or update local projection).

---

## 🧠 2. Patterns for Running Kafka Consumer in FastAPI

There are 3 good options:

| Approach                            | Description                                                                          | When to use                            |
| ----------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------- |
| **Background Task in FastAPI**      | Start a consumer loop with `asyncio.create_task()` inside `@app.on_event("startup")` | ✅ Best for assignments and simple apps |
| Separate process/container          | Run consumer script separately (`consumer.py`)                                       | For production scaling                 |
| ThreadPoolExecutor or Celery worker | For heavy processing workloads                                                       | Overkill for now                       |

✅ For your assignment → use **background async task** within the FastAPI app.

---

## ⚙️ 3. Implementation Example

We’ll extend the **User Service** to include a Kafka consumer that listens to `order_created`.

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
    # Initialize database and start the Kafka consumer loop
    init_db()
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

    # Produce Kafka event after commit
    background_tasks.add_task(produce_event, "user_created", {
        "user_id": new_user.id,
        "email": new_user.email,
        "name": new_user.name
    })
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

### `user_service/app/kafka_consumer.py`

```python
import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

async def consume_order_events():
    """
    This function runs as a background task started from main.py
    It listens for 'order_created' events emitted by the Order Service.
    """
    consumer = AIOKafkaConsumer(
        "order_created",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="user_service_group",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    print("[UserService] Kafka consumer started for 'order_created'")
    try:
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print(f"[UserService] Received order_created event: {event}")
            # Example handling:
            # You could store a local record of this order in your users_db
            # e.g. record_order_reference(event)
    except Exception as e:
        print("[UserService] Consumer error:", e)
    finally:
        await consumer.stop()
        print("[UserService] Kafka consumer stopped")
```

---

### `user_service/app/kafka_producer.py`

(same as before)

```python
import os, asyncio, json
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
_producer = None

async def get_producer():
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
        await _producer.start()
    return _producer

async def produce_event(topic: str, event: dict):
    producer = await get_producer()
    await producer.send_and_wait(topic, json.dumps(event).encode("utf-8"))
```

---

### Example Logs

Run everything and you’ll see:

```
[UserService] Kafka consumer started for 'order_created'
...
[OrderService] Created new order: {"order_id": 1, "user_id": 1}
[UserService] Received order_created event: {"order_id": 1, "user_id": 1}
```

That’s exactly the event flow your assignment is testing for.

---

## 🧱 4. Typical Ways to Handle the Incoming `order_created` Event

Once the user service receives `order_created`, it can:

| Purpose                    | Example                                         |
| -------------------------- | ----------------------------------------------- |
| **Log or audit**           | Keep a log of all orders created for monitoring |
| **Update a local cache**   | Add an entry to a `user_orders` table           |
| **Emit a follow-up event** | `user_order_summary_updated`                    |
| **Send notification**      | Email or message to user (simulated in code)    |

Example DB model addition if you want to record orders locally:

```python
# user_service/app/models.py
class UserOrder(Base):
    __tablename__ = "user_orders"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, unique=True)
    user_id = Column(Integer)
    amount = Column(Numeric(10,2))
```

Then inside `consume_order_events()`:

```python
from .db import SessionLocal
from .models import UserOrder

session = SessionLocal()
order = UserOrder(order_id=event["order_id"], user_id=event["user_id"], amount=event.get("amount"))
session.add(order)
session.commit()
session.close()
```

---

## 🐋 5. Docker Setup Recap

No major change — still **one container per service**:

* `user_service` has both API and Kafka consumer (in same FastAPI process).
* `order_service` does the same (consuming `user_created`).

Your `docker-compose.yml` stays identical — you just make sure:

```yaml
user_service:
  environment:
    - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

and that the network allows them to reach Kafka.

---

## 🧭 6. Key Takeaways (for report / writeup)

> The User Service consumes `order_created` Kafka events to remain eventually consistent with the Order Service’s data.
> Both services host a FastAPI instance for REST access and run an asynchronous Kafka consumer loop started at application startup.
> This ensures bi-directional event-driven communication while preserving database autonomy and service isolation.

That’s textbook microservice reasoning. ✅

---

Would you like me to show you the **Order Service**’s symmetrical setup (how it consumes `user_created` while running its API) — so you have a full two-way example you can paste into your repo?
