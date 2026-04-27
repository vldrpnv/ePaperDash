from __future__ import annotations

import time
from typing import Callable, Protocol

import paho.mqtt.client as mqtt

from epaper_dashboard_service.domain.models import MqttConfig
from epaper_dashboard_service.domain.ports import DashboardPublisher


class MqttClientLike(Protocol):
    def username_pw_set(self, username: str, password: str | None = None) -> None: ...
    def connect(self, host: str, port: int) -> None: ...
    def publish(self, topic: str, payload: bytes, qos: int, retain: bool): ...
    def disconnect(self) -> None: ...


class MqttDashboardPublisher(DashboardPublisher):
    def __init__(
        self,
        config: MqttConfig,
        client: MqttClientLike | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._config = config
        self._client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.client_id)
        self._sleeper = sleeper or time.sleep

    def publish(self, payload: bytes) -> None:
        attempts = max(1, self._config.publish_retry_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                if self._config.username:
                    self._client.username_pw_set(self._config.username, self._config.password)
                self._client.connect(self._config.host, self._config.port)
                result = self._client.publish(
                    topic=self._config.topic,
                    payload=payload,
                    qos=self._config.qos,
                    retain=self._config.retain,
                )
                if getattr(result, "rc", mqtt.MQTT_ERR_UNKNOWN) != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"publish rc={result.rc}")
                return
            except Exception as error:
                last_error = error
                if attempt < attempts:
                    self._sleeper(max(0.0, self._config.publish_retry_delay_seconds))
            finally:
                try:
                    self._client.disconnect()
                except Exception:
                    pass

        raise RuntimeError(f"Failed to publish dashboard image after {attempts} attempts") from last_error
