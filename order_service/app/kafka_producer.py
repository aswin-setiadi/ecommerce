from decimal import Decimal
import json
import logging
import os

from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
logger = logging.getLogger(__name__)
producer = None

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Implement custom serialization logic if needed
        if isinstance(obj,Decimal):
            return float(obj)
        return super().default(obj)

async def get_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
    return producer

async def produce_event(topic: str, event: dict):
    producer = await get_producer()
    try:
        event_bytes = json.dumps(event, cls= CustomJSONEncoder).encode('utf-8')
    except TypeError as e:
        logger.exception(e)
        raise
    await producer.send_and_wait(topic, event_bytes)
    logger.info(f"Produced event to topic {topic}: {event}")
