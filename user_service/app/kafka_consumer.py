import asyncio
import json
import logging
import os
import time
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from .db import SessionLocal
from .models import CachedOrder

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
logger= logging.getLogger(__name__)

async def consume_order_events():
    while True:
        try:
            consumer = AIOKafkaConsumer(
                "order_created",
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="user_service_group",
                auto_offset_reset="earliest" # Start from the beginning of the topic if no offset is committed, can be changed as needed
            )
            break
        except KafkaConnectionError as e:
            logger.error(f"[UserService] Kafka connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    await consumer.start()
    try:
        logger.info("[UserService] Kafka consumer started for 'order_created'")
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            logger.info(f"[UserService] Received order_created event: {event}")
            # Could update DB or record reference if needed
            with SessionLocal() as session:
                with session.begin(): #commit write operation if no exception, rollback  otherwise
                    cached= session.query(CachedOrder).filter_by(id=event["id"]).first()
                    if not cached:
                        new_cached= CachedOrder(
                            id= event["id"],
                            user_id= event["user_id"]
                        )
                        session.add(new_cached)
                        logger.info(f"[UserService] Cached new order: {new_cached.to_dict()}")
    except asyncio.CancelledError:
        logger.info("Consumer task fully cancelled during shutdown")
    finally:
        await consumer.stop()
