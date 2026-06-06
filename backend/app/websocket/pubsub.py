"""
Redis Pub/Sub for real-time shortage alerts
============================================
Publishes shortage events to Redis channels so that any connected
WebSocket clients (across multiple Uvicorn workers) receive real-time alerts.

Channel naming convention:  shortage:<blood_group_value>
                             shortage:ALL  (for universal broadcasts)

Usage:
    from app.websocket.pubsub import publish_shortage
    await publish_shortage("A+", "Critical shortage of A+ blood in your area!")
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def publish_shortage(blood_group: str, message: str, city: Optional[str] = None):
    """
    Publish a shortage alert to Redis.
    Falls back gracefully if Redis is unavailable.
    """
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        payload = json.dumps({
            "type": "shortage_alert",
            "blood_group": blood_group,
            "message": message,
            "city": city,
        })
        channel = f"shortage:{blood_group}"
        await r.publish(channel, payload)
        # Also broadcast to ALL channel so global listeners can pick it up
        await r.publish("shortage:ALL", payload)
        await r.aclose()
        logger.info("📢 Published shortage alert for %s to Redis", blood_group)
    except Exception as exc:
        # Never crash the caller — shortage broadcast is best-effort
        logger.warning("⚠️  Redis pub/sub unavailable: %s", exc)
