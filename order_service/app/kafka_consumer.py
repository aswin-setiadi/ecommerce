import asyncio
import json
import logging
import os
import time

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from .db import SessionLocal
from .models import CachedUser

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
logger= logging.getLogger(__name__)
async def consume_user_events():
    """Background task that consumes 'user_created' events from Kafka and caches users in the local database.
    """
    while True:
        try:
            consumer = AIOKafkaConsumer(
                "user_created",
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="order_service_group",
                auto_offset_reset="earliest"
            )
            break
        except KafkaConnectionError as e:
            logger.error(f"[OrderService] Kafka connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    await consumer.start()
    try:
        logger.info("[OrderService] Kafka consumer started for 'user_created'")
        async for msg in consumer:
            event = json.loads(msg.value.decode("utf-8"))
            logger.info(f"[OrderService] Received user_created event: {event}")
            db= SessionLocal()
            try:
                cached= db.query(CachedUser).filter_by(id=event["id"]).first()
                if not cached:
                    new_cached= CachedUser(id= event["id"])
                    db.add(new_cached)
                    db.commit()
                    logger.info(f"[OrderService] Cached new user: {new_cached.to_dict()}")
            except Exception as e:
                logger.exception(e)
                db.rollback()
            finally:
                db.close()

    except asyncio.CancelledError:
        logger.info("Consumer task fully cancelled during shutdown")
    finally:
        await consumer.stop()
