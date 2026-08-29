"""Fire-and-forget audit event publisher (RabbitMQ)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from structlog.contextvars import get_contextvars

logger = structlog.get_logger()


class AuditEventPublisher:
    def __init__(self) -> None:
        self.enabled = os.getenv("AUDIT_ENABLED", "true").lower() not in ("0", "false", "no")
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", os.getenv("RABBITMQ_DEFAULT_USER", "guest"))
        self.password = os.getenv("RABBITMQ_PASSWORD", os.getenv("RABBITMQ_DEFAULT_PASS", "guest"))
        self.vhost = os.getenv("RABBITMQ_VHOST", "/")
        self.exchange = os.getenv("AUDIT_EXCHANGE", "srv-audit-exchange-local")
        self.routing_key = os.getenv("AUDIT_ROUTING_KEY", "audit.event")

    def publish(
        self,
        action: str,
        outcome: str,
        correlation_id: Optional[str],
        resource_type: str = "TOKEN",
        resource_id: str = "",
    ) -> None:
        if not self.enabled:
            return
        cid = correlation_id or self._correlation_from_context() or str(uuid.uuid4())
        event = {
            "eventId": str(uuid.uuid4()),
            "occurredAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "schemaVersion": 1,
            "sourceService": "srv-token-manager",
            "correlationId": cid,
            "action": action,
            "outcome": outcome,
            "actor": {"type": "SYSTEM"},
            "resource": {"type": resource_type, "id": resource_id},
        }
        thread = threading.Thread(target=self._send, args=(event, cid), daemon=True)
        thread.start()

    def _send(self, event: dict[str, Any], correlation_id: str) -> None:
        try:
            import pika

            credentials = pika.PlainCredentials(self.user, self.password)
            params = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost or "/",
                credentials=credentials,
                blocked_connection_timeout=5,
                socket_timeout=5,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=json.dumps(event).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    headers={"X-Correlation-ID": correlation_id},
                ),
            )
            connection.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("audit_publish_failed", action=event.get("action"), error=str(exc))

    def _correlation_from_context(self) -> Optional[str]:
        try:
            cid = get_contextvars().get("correlationId")
            if isinstance(cid, str) and cid.strip():
                return cid.strip()
        except Exception:  # noqa: BLE001
            return None
        return None
