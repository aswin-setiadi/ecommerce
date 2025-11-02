import asyncio
import json
import pytest
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from testcontainers.kafka import KafkaContainer

@pytest.mark.asyncio
async def test_kafka_integration_user_service():
    with KafkaContainer() as kafka:
        broker = kafka.get_bootstrap_server()
        producer = AIOKafkaProducer(bootstrap_servers=broker)
        consumer = AIOKafkaConsumer("order_created", bootstrap_servers=broker)
        await producer.start()
        await consumer.start()

        await producer.send_and_wait("order_created", json.dumps({
            "id": 1,
            "product":"coffee",
            "quantity":100,
            "total_price":50,
            "user_id":3
        }).encode("utf-8"))
        msg = await consumer.getone()
        event = json.loads(msg.value.decode())

        assert event["user_id"] == 1

        await producer.stop()
        await consumer.stop()
