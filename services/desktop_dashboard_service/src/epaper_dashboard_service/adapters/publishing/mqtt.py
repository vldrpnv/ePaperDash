from __future__ import annotations

from typing import Protocol

import paho.mqtt.client as mqtt

from epaper_dashboard_service.domain.models import MqttConfig
from epaper_dashboard_service.domain.ports import DashboardPublisher


class MqttClientLike(Protocol):
    def username_pw_set(self, username: str, password: str | None = None) -> None: ...
    def connect(self, host: str, port: int) -> None: ...
    def publish(self, topic: str, payload: bytes, qos: int, retain: bool): ...
    def disconnect(self) -> None: ...


class MqttDashboardPublisher(DashboardPublisher):
    def __init__(self, config: MqttConfig, client: MqttClientLike | None = None) -> None:
        self._config = config
        self._client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.client_id)

    def publish(self, payload: bytes) -> None:
        if self._config.username:
            self._client.username_pw_set(self._config.username, self._config.password)
        self._client.connect(self._config.host, self._config.port)
        result = self._client.publish(
            topic=self._config.topic,
            payload=payload,
            qos=self._config.qos,
            retain=self._config.retain,
        )
        if getattr(result, "rc", 0) != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Failed to publish dashboard image: rc={result.rc}")
        self._client.disconnect()
