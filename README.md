# Event-drivent Ecommerce Task

I have no experience in ecommerce development so I will start by asking AI tool (copilot or chatgpt) on the task requirement. I will analyse the response and write my thoughts then adjust the response code during implementation when needed. These adjustment should be tracked in the Analysis and Work Notes section.

## Installation

```bash
git clone https://github.com/aswin-setiadi/ecommerce.git TakeHomeTest
cd TakeHomeTest
mkdir -p logs/order_service
mkdir -p logs/user_service
mkdir -p order_service/db/data
mkdir -p user_service/db/data
docker-compose up --build
```

## Testing

It is recommended to comment out user_postgres and order_postgres volumes in docker-compose.yml so the user_id created start at 1. This is also to prevent persisting test data.

1. Create user

```bash
curl  -X POST \
  'http://localhost:8001/users' \
  --header 'Accept: */*' \
  --header 'User-Agent: Thunder Client (https://www.thunderclient.com)' \
  --header 'Content: application/json' \
  --header 'Content-Type: application/json' \
  --data-raw '{"email":"setiadi@example.com", "name":"Setiadi"}'
```

2. Get the created user

```bash
curl  -X GET \
  'http://localhost:8001/users/1' \
  --header 'Accept: */*'
```

3. Create order

```bash
curl  -X POST \
  'http://localhost:8002/orders' \
  --header 'Accept: */*' \
  --header 'Content-Type: application/json' \
  --data-raw '{
  "product":"coffee",
  "quantity":100,
  "total_price":50,
  "user_id":1
}'
```

4. Get the created order

```bash
curl  -X GET \
  'http://localhost:8002/orders/1' \
  --header 'Accept: */*'
```

5. Create user with existing email

```bash
curl  -X POST \
  'http://localhost:8001/users' \
  --header 'Accept: */*' \
  --header 'User-Agent: Thunder Client (https://www.thunderclient.com)' \
  --header 'Content: application/json' \
  --header 'Content-Type: application/json' \
  --data-raw '{"email":"setiadi@example.com", "name":"Setiadi"}'
```

6. Create order with the same payload as 3

```bash
curl  -X POST \
  'http://localhost:8002/orders' \
  --header 'Accept: */*' \
  --header 'Content-Type: application/json' \
  --data-raw '{
  "product":"coffee",
  "quantity":100,
  "total_price":50,
  "user_id":1
}'
```

## Analysis

### Architect overview

The task requires us to implement event-driven (Kafka) microservices. The user service create model of user with id, name, and email. Pydantic helps validate email, and the sqlalchemy tools indicate fields to index/ unique. The get method is quite straightforward. The order service create model of order with id, user_id, name, and email. Since the project is using microservice architecture, each service own it's own database, so that migration, database selection/ failure are isolated to that service only. When combining data from different services/ databases, the kafka communication act as a syncer between the services (specifically for operation: write, update, delete). As long as those events are handle by the other services, the service ecosystem will eventually synced up/ consistent, yet with the flexibility of loosely coupled setup. Kafka can be taken as an event bus where we can replay the sequence of object operation to recreate the latest state of objects in different services. This resiliency is critical should a disaster happen to the live production servers. I can foresee the order operation will be much more frequent than user operation, with the microservice approach, it will be easy to scale the resource to support order.

### Security

Due to the limited time developing this project, in production, these can be implemented :

1. We can apply jwt authentication for the APIs, as well as session permission check (authorization).

2. Using 3rd part secret management for storing username and password instead of raw text in environment variable (through resource role/ permission, etc.).

### Future Improvements

1. Using outbox pattern, where data changing operation is captured and save in a temporary table together with the data changing operation (atomic operation), where a separate service poll this table and publish them to kafka (reliability should the kafka service is down, the table persist, waiting for the kafka service to recover and continue consuming). This polling can further be improved by replacing it with database transaction as change data capture.

2. Using nginx to help with routing, security (DDoS mitigation), SSL/TLS termination and rate limiting.

3. Create environment specific docker-compose.yml, requirements.txt, and Dockerfile (dev env using directory mount for quick iteration and testing vs python wheel in production, raw text credentials and dev env configuration for fastapi, kafka, postgresql vs production configuration stored in secret manager service, testing module installation for dev environment, etc.).

## Work Notes

For user model, I assume a person with multiple email is allowed to create multiple user account, so I make name field non unique.

In the schema, the Config class within create schema seems to allow pydantic to create pydantic model instance from ORM object through `from_orm` method.

The FastAPI title arg. is mostly used for documentation meta info.

The chatgpt response seems to use deprecated `@app.on_event` decorator. I follow linter suggestion and use lifespan callback as arg. Followed example in the fastapi page.

I added `ToDictMixIn` to help mapping sqlachemy model to dictionary with keys equal the model fields. This helps a lot in reducing manual mapping of keys.


[Prompt 13](misc/PROMPTS.md#prompt_13)

Thought: I think seperating db is good when we have large teams, each owning seperate services. In this case, any database migration risk/ maintenance down time are isolated to each service.

There is an issue when pulling zookeeper and kafka image where Bitnami moved its public catalog to bitnamilegacy, updated the url accordingly in docker-compose.

Bitnami kafka v3.8+ will always use KRaft mode, change tag to kafka:3.7.1 and add KAFKA_ENABLE_KRAFT=no.

For Bitnami image, when restarting kafka, it autoassign the broker id if not declared. During startup, kafka will register its brokerid to zookeeper. When restarting service, if the same kafka:9092 advertise itself but different brokerid, zookeeper will reject the second one.

After some reading, decided to use apache kafka image with KRaft.

Change permission for run.sh (container can't execute) and logs/kafka (kafka can't write logs in the mounted folder).

Add file logging.

Mount python folder instead of copy (faster development iteration). In production, can wheel the python program as a module, then add it to requirements.txt.


1. remove env connection str default value in code to fail early should the env. variable list are wrong/ incomplete.

## Reference

1. <https://stackoverflow.com/questions/19143345/about-refreshing-objects-in-sqlalchemy-session>

2. <https://fastapi.tiangolo.com/advanced/events/#lifespan>

3. <https://stackoverflow.com/questions/76345708/passing-kwargs-via-dict-to-a-function-and-overwriting-a-single-passed-kwarg-in-a>

4. <https://www.reddit.com/r/microservices/comments/17p2zrk/does_microservices_architecture_requires_a/>

5. <https://www.reddit.com/r/FastAPI/comments/1mq7ed8/lifespan_on_fastapi/>

6. <https://hub.docker.com/r/bitnami/zookeeper>

7. <https://www.datacamp.com/tutorial/kafka-docker-explained>