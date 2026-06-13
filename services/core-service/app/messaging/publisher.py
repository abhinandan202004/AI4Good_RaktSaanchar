"""
RabbitMQ Publisher — core-service
Publishes blood request lifecycle events.
"""
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional

import aio_pika

from app.core.config import settings

logger = logging.getLogger(__name__)
EXCHANGE_NAME = "raktsaanchar"


async def _publish(routing_key: str, payload: Dict[str, Any]) -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
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
        logger.warning("RabbitMQ publish failed (key=%s): %s", routing_key, exc)


def _fire(routing_key: str, payload: Dict[str, Any]) -> None:
    """Fire-and-forget — schedules publish on the running event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_publish(routing_key, payload))
        else:
            loop.run_until_complete(_publish(routing_key, payload))
    except Exception as exc:
        logger.warning("Event scheduling failed: %s", exc)


def publish_blood_request_created(
    request_id: int,
    blood_group: str,
    urgency: str,
    units_required: int,
    patient_id: int,
    patient_user_id: int,
    patient_city: Optional[str],
    patient_lat: Optional[float],
    patient_lon: Optional[float],
    hospital: str,
    top_donors: Optional[List[dict]] = None,
) -> None:
    _fire("blood_request.created", {
        "event": "blood_request.created",
        "request_id": request_id,
        "blood_group": blood_group,
        "urgency": urgency,
        "units_required": units_required,
        "patient_id": patient_id,
        "patient_user_id": patient_user_id,
        "patient_city": patient_city,
        "patient_lat": patient_lat,
        "patient_lon": patient_lon,
        "hospital": hospital,
        "top_donors": top_donors or [],
    })


def publish_blood_request_matched(
    request_id: int, donor_user_id: int, patient_user_id: int
) -> None:
    _fire("blood_request.matched", {
        "event": "blood_request.matched",
        "request_id": request_id,
        "donor_user_id": donor_user_id,
        "patient_user_id": patient_user_id,
    })


def publish_blood_request_accepted(
    request_id: int,
    donor_user_id: int,
    patient_user_id: int,
    donor_name: str = "",
    patient_name: str = "",
) -> None:
    _fire("blood_request.accepted", {
        "event": "blood_request.accepted",
        "request_id": request_id,
        "donor_user_id": donor_user_id,
        "patient_user_id": patient_user_id,
        "donor_name": donor_name,
        "patient_name": patient_name,
    })


def publish_blood_request_fulfilled(
    request_id: int,
    donor_user_id: int,
    patient_user_id: int,
    donor_id: int,
) -> None:
    _fire("blood_request.fulfilled", {
        "event": "blood_request.fulfilled",
        "request_id": request_id,
        "donor_user_id": donor_user_id,
        "patient_user_id": patient_user_id,
        "donor_id": donor_id,
    })


def publish_badge_awarded(
    donor_user_id: int, badge_name: str, badge_icon: str = "🏅"
) -> None:
    _fire("badge.awarded", {
        "event": "badge.awarded",
        "donor_user_id": donor_user_id,
        "badge_name": badge_name,
        "badge_icon": badge_icon,
    })
