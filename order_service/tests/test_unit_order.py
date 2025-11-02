import pytest
from unittest.mock import patch
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

@patch("app.kafka_producer.produce_event")
def test_create_user_emits_event(mock_kafka):
    payload = {
        "product":"coffee",
        "quantity":100,
        "total_price":50,
        "user_id":3
    }
    resp = client.post("/orders", json=payload)
    assert resp.status_code == 200
    mock_kafka.assert_called_once()
