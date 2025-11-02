# Event-drivent Ecommerce Task

I have no experience in ecommerce development, so I will start by asking AI tool (copilot or chatgpt) on the task requirement. I will analyse the response and write my thoughts then adjust the respond if needed. These adjustment should be tracked through the code commit messages.

## Workflow

For user model, I assume a person with multiple email is allowed to create multiple user account, so I make name field non unique.

For order price field, it is ambigue (price per item or total price) so I rename it to total_price.

In the schema, the Config class within create schema seems to allow pydantic to create pydantic model instance from ORM object through `from_orm` method.

The FastAPI title is mostly used for documentation meta info.

The chatgpt response seems to use deprecated `@app.on_event` decorator. I follow linter suggestion and use lifespan.

[Prompt 13](misc/PROMPTS.md#prompt_13)

Thought: I think seperating db is good when we have large teams, each owning seperate services. In this case, any database migration risk/ maintenance down time are isolated to each service.

There is an issue when pulling zookeeper and kafka image where Bitnami moved its public catalog to bitnamilegacy, updated the url accordingly in docker-compose.

Bitnami kafka v3.8+ will always use KRaft mode, change tag to kafka:3.7.1 and add KAFKA_ENABLE_KRAFT=no.


For Bitnami image, when restarting kafka, it autoassign the broker id if not declared. During startup, kafka will register its brokerid to zookeeper. When restarting service, if the same kafka:9092 advertise itself but different brokerid, zookeeper will reject the second one.

## Improvements

1. remove env connection str default value in code to fail early should the env. variable list are wrong/ incomplete.

## Reference

1. <https://stackoverflow.com/questions/19143345/about-refreshing-objects-in-sqlalchemy-session>

2. <https://fastapi.tiangolo.com/advanced/events/#lifespan>

3. <https://stackoverflow.com/questions/76345708/passing-kwargs-via-dict-to-a-function-and-overwriting-a-single-passed-kwarg-in-a>

4. <https://www.reddit.com/r/microservices/comments/17p2zrk/does_microservices_architecture_requires_a/>

5. <https://www.reddit.com/r/FastAPI/comments/1mq7ed8/lifespan_on_fastapi/>

6. <https://hub.docker.com/r/bitnami/zookeeper>