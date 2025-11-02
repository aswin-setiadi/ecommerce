import json
import logging
import os

from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
logger= logging.getLogger(__name__)
producer = None

async def get_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
    return producer

async def produce_event(topic: str, event: dict):
    producer = await get_producer()
    event_bytes = json.dumps(event).encode('utf-8')
    await producer.send_and_wait(topic, event_bytes)
