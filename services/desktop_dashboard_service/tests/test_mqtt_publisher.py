from __future__ import annotations

from types import SimpleNamespace

import paho.mqtt.client as mqtt
import pytest

from epaper_dashboard_service.adapters.publishing.mqtt import MqttDashboardPublisher
from epaper_dashboard_service.domain.models import MqttConfig


class FlakyConnectClient:
    def __init__(self, failures_before_success: int) -> None:
        self.failures_before_success = failures_before_success
        self.connect_calls = 0
        self.publish_calls = 0
        self.disconnect_calls = 0

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        return None

    def connect(self, host: str, port: int) -> None:
        self.connect_calls += 1
        if self.connect_calls <= self.failures_before_success:
            raise TimeoutError("broker timeout")

    def publish(self, topic: str, payload: bytes, qos: int, retain: bool):
        self.publish_calls += 1
        return SimpleNamespace(rc=mqtt.MQTT_ERR_SUCCESS)

    def disconnect(self) -> None:
        self.disconnect_calls += 1


class FailingPublishClient:
    def __init__(self) -> None:
        self.connect_calls = 0
        self.publish_calls = 0
        self.disconnect_calls = 0

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        return None

    def connect(self, host: str, port: int) -> None:
        self.connect_calls += 1

    def publish(self, topic: str, payload: bytes, qos: int, retain: bool):
        self.publish_calls += 1
        return SimpleNamespace(rc=mqtt.MQTT_ERR_NO_CONN)

    def disconnect(self) -> None:
        self.disconnect_calls += 1


def test_mqtt_publisher_retries_connect_then_succeeds() -> None:
    client = FlakyConnectClient(failures_before_success=1)
    delays: list[float] = []
    publisher = MqttDashboardPublisher(
        config=MqttConfig(
            host="localhost",
            port=1883,
            topic="epaper/image",
            publish_retry_attempts=3,
            publish_retry_delay_seconds=0.25,
        ),
        client=client,
        sleeper=delays.append,
    )

    publisher.publish(b"payload")

    assert client.connect_calls == 2
    assert client.publish_calls == 1
    assert delays == [0.25]


def test_mqtt_publisher_retries_and_raises_when_broker_unavailable() -> None:
    client = FailingPublishClient()
    delays: list[float] = []
    publisher = MqttDashboardPublisher(
        config=MqttConfig(
            host="localhost",
            port=1883,
            topic="epaper/image",
            publish_retry_attempts=3,
            publish_retry_delay_seconds=0.5,
        ),
        client=client,
        sleeper=delays.append,
    )

    with pytest.raises(RuntimeError, match="Failed to publish dashboard image after 3 attempts"):
        publisher.publish(b"payload")

    assert client.connect_calls == 3
    assert client.publish_calls == 3
    assert client.disconnect_calls == 3
    assert delays == [0.5, 0.5]
