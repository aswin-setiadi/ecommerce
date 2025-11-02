import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer
from .db import SessionLocal
from .models import CachedUser

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")

async def consume_user_events():
    try:
        consumer = AIOKafkaConsumer(
            "user_created",
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="order_service_group",
            auto_offset_reset="earliest"
        )
        await consumer.start()
        print("[OrderService] Kafka consumer started for 'user_created'")
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print(f"[OrderService] Received user_created event: {event}")
            db= SessionLocal()
            cached= db.query(CachedUser).filter_by(id=event["id"]).first()
            if not cached:
                new_cached= CachedUser(
                    id= event["id"],
                    name= event["name"],
                    email= event["email"]
                )
                db.add(new_cached)
                db.commit()
                print(f"[OrderService] Cached new user: {new_cached}")
            db.close()

    except asyncio.CancelledError:
        print("Cosnumer task fully cancelled during shutdown")
    finally:
        await consumer.stop()
