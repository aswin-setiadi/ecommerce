Perfect 👍 — let’s complete the setup with a clean **Kafka + Docker Compose** architecture that supports *bi-directional event-driven communication* between the **User Service** and the **Order Service**.

This will give you a working baseline you can both *run locally* and *explain confidently* in your assignment report.

---

## 🧩 1. Architecture Overview

### Services and Event Flow

| Service           | Produces               | Consumes        | Database    |
| ----------------- | ---------------------- | --------------- | ----------- |
| **User Service**  | `user_created`         | `order_created` | `users_db`  |
| **Order Service** | `order_created`        | `user_created`  | `orders_db` |
| **Kafka**         | central message broker | —               | —           |
| **Zookeeper**     | required by Kafka      | —               | —           |

### Event Flow Diagram

```
   [User API] ---> user_created ---> [Kafka topic: user_created] ---> [Order Service consumer]
   [Order API] ---> order_created ---> [Kafka topic: order_created] ---> [User Service consumer]
```

---

## 🐋 2. Docker Compose Configuration

Here’s a minimal but **fully working `docker-compose.yml`** for your setup:

```yaml
version: "3.9"

services:
  zookeeper:
    image: bitnami/zookeeper:latest
    container_name: zookeeper
    environment:
      - ALLOW_ANONYMOUS_LOGIN=yes
    ports:
      - "2181:2181"

  kafka:
    image: bitnami/kafka:latest
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_LISTENERS=PLAINTEXT://:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - ALLOW_PLAINTEXT_LISTENER=yes

  user_service:
    build: ./user_service
    container_name: user_service
    depends_on:
      - kafka
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - DATABASE_URL=postgresql+psycopg2://postgres:postgres@user_db:5432/users
    ports:
      - "8001:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  order_service:
    build: ./order_service
    container_name: order_service
    depends_on:
      - kafka
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - DATABASE_URL=postgresql+psycopg2://postgres:postgres@order_db:5432/orders
    ports:
      - "8002:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  user_db:
    image: postgres:15
    container_name: user_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=users
    ports:
      - "5433:5432"

  order_db:
    image: postgres:15
    container_name: order_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=orders
    ports:
      - "5434:5432"

networks:
  default:
    name: ecommerce-net
```

---

## 🧠 3. Directory Structure

Your project should look like this:

```
ecommerce-backend/
│
├── docker-compose.yml
├── user_service/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── kafka_consumer.py
│   │   └── kafka_producer.py
│   └── requirements.txt
│
└── order_service/
    ├── Dockerfile
    ├── app/
    │   ├── main.py
    │   ├── db.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── kafka_consumer.py
    │   └── kafka_producer.py
    └── requirements.txt
```

---

## 🧱 4. Example Dockerfiles

Both microservices will have nearly identical `Dockerfile`s.

### `user_service/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `order_service/Dockerfile`

(same as above)

---

## 📦 5. requirements.txt (both services)

```text
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
aiokafka
pydantic
```

---

## 🚀 6. Running the system

```bash
docker-compose up --build
```

When everything is up, you’ll have:

| Service           | URL                                            | Description       |
| ----------------- | ---------------------------------------------- | ----------------- |
| User API          | [http://localhost:8001](http://localhost:8001) | Create/get users  |
| Order API         | [http://localhost:8002](http://localhost:8002) | Create/get orders |
| Kafka             | localhost:9092                                 | Event broker      |
| Postgres (users)  | localhost:5433                                 | Users DB          |
| Postgres (orders) | localhost:5434                                 | Orders DB         |

---

## 🧾 7. Example Interaction

### 1️⃣ Create a user

```bash
curl -X POST http://localhost:8001/users \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com", "name":"Alice"}'
```

✅ This triggers:

* DB insert in `users_db`
* Kafka event `user_created`
* Order Service consumes that event → stores in `users_cache`

---

### 2️⃣ Create an order

```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id":1, "amount": 100.50}'
```

✅ This triggers:

* DB insert in `orders_db`
* Kafka event `order_created`
* User Service consumes it → can store or log user’s order.

---

### 3️⃣ View the results

You’ll see logs like:

```
[UserService] Received order_created event: {"order_id":1,"user_id":1,"amount":"100.50"}
[OrderService] Received user_created event: {"user_id":1,"email":"alice@example.com","name":"Alice"}
```

---

## 🧭 8. What to explain in your report

> Each service runs independently with its own database, exposing its own REST API through FastAPI. Kafka acts as the event bus that synchronizes data between services asynchronously.
> The User Service emits `user_created` events consumed by the Order Service, which maintains a local user cache for validation. Conversely, the Order Service emits `order_created` events consumed by the User Service for audit or projection purposes.
> Docker Compose orchestrates the microservices, databases, and Kafka broker in an isolated network, demonstrating full event-driven microservice architecture.

---

Would you like me to show the **minimal working code for the Order Service** (with user cache + Kafka producer/consumer) so you can test this end-to-end right away?
