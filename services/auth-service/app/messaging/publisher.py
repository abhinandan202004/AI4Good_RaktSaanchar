"""
RabbitMQ Publisher — auth-service
Publishes events: otp.send, user.registered
"""
import json
import logging
import asyncio
from typing import Any, Dict

import aio_pika

from app.core.config import settings

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "raktsaanchar"


async def _publish(routing_key: str, payload: Dict[str, Any]) -> None:
    """Connect, publish one message, disconnect."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            logger.info("📤 Published event '%s'", routing_key)
    except Exception as exc:
        # Publishing failures must NOT crash the request — they are best-effort
        logger.warning("RabbitMQ publish failed (key=%s): %s", routing_key, exc)


def publish_otp_send(user_id: int, email: str, full_name: str, otp_code: str) -> None:
    """
    Publish otp.send event so notification-service can also send push/email.
    For auth-service the OTP email is sent directly; this event is informational.
    """
    payload = {
        "event": "otp.send",
        "user_id": user_id,
        "email": email,
        "full_name": full_name,
        "otp_code": otp_code,
    }
    asyncio.create_task(_publish("otp.send", payload))


def publish_user_registered(
    user_id: int,
    email: str,
    phone: str | None,
    full_name: str,
    role: str,
) -> None:
    """
    Publish user.registered so core-service and other consumers can cache
    basic user information locally without calling auth-service.
    """
    payload = {
        "event": "user.registered",
        "user_id": user_id,
        "email": email,
        "phone": phone,
        "full_name": full_name,
        "role": role,
    }
    asyncio.create_task(_publish("user.registered", payload))
