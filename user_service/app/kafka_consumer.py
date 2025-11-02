import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

async def consume_order_events():
    try:
        consumer = AIOKafkaConsumer(
            "order_created",
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="user_service_group",
            auto_offset_reset="earliest" # Start from the beginning of the topic if no offset is committed, can be changed as needed
        )
        await consumer.start()
        print("[UserService] Kafka consumer started for 'order_created'")
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            print(f"[UserService] Received order_created event: {event}")
            # Could update DB or record reference if needed
    except asyncio.CancelledError:
        print("Cosnumer task fully cancelled during shutdown")
    finally:
        await consumer.stop()
