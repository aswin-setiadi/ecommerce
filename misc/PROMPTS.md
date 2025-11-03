# LLM Prompts

## Prompts History

<a id="prompt_0"></a>

1. (chatgpt)
    1. I have a programming assignment that ask me to implement an ecommerce backend in python using sqlalchemy deployed as microservice through docker compose. The api requires creation and retrieval of users and orders. The task requires me to use kafka for communication between microservice and choose the best architecture decision
    2. I want the user and order to be a different service and each creation kafka event should be consumed by the other service
    3. what is the reason the user and order db is seperated? Is it bad to have them in the same database?
    4. for the user service, the assignment requires it to also consume the order service creation event. How should I set it up along with the api
    5. it seems the order creation does not validate if the user_id is valid
    6. yes

2. (copilot) I have an assignment to create an ecommerce backend using python and sqlalchemy. The backend has user and order service, each having create and retrieval api. Each create event should trigger kafka event that the other service will consume. The services, kafka, and sql should be deployed through docker compose.

3. (gemini) what is the purpose of sqlalchemy relationship and back_populates, give me a concrete example to exhibit the usefulness

4. (gemini) what is pydantic basemodel config class orm_mode true

5. (gemini) fastapi lifespan example for initializing db

6. (gemini) does sqlalchemy session refresh necessary after adding and commiting

7. (gemini) in sqlalchemy if the model has relationship back_populates do we need to call session refresh after add and commit

8. (gemini) sqlalchemy declarative_base create custom method

9. (gemini) does pydantic obj support ** to pass as arg

10. (gemini) can I use pydantic obj with ** without model_dump but just the obj itself

11. (gemini)
    1. can I use async await without explicitly import asyncio module
    2. so I have to declare import asyncio, but I'm not referencing the asyncio module in my code which consume kafka message, if I comment out import asyncio, will it break

12. (gemini)
    1. I have fastapi lifespan that create async kafka consumer task, do I need to manually stop the consumer when the app stop
    2. but it seems the code already has finally await consumer.stop()

13. (gemini) why event driven architecture use seperate database

14. (gemini) do I need to set sleep for python async kafka consumer where it use async for msg in consumer

15. (chatgpt) my kafka container getting error requirement failed: Configured end points kafka:9092 in advertised listeners are already registered by broker 1002