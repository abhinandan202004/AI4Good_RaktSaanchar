"""
RabbitMQ Consumer — chat-service
Listens to blood_request.accepted and auto-creates chat rooms.
Also pushes chat message notifications via ntfy.
"""
import json
import logging

import aio_pika

from app.core.config import settings

logger = logging.getLogger(__name__)
EXCHANGE_NAME = "raktsaanchar"


async def handle_blood_request_accepted(event: dict) -> None:
    """Auto-create a chat room when a blood request is accepted."""
    request_id = event.get("request_id")
    donor_user_id = event.get("donor_user_id")
    patient_user_id = event.get("patient_user_id")

    if not all([request_id, donor_user_id, patient_user_id]):
        logger.warning("blood_request.accepted event missing required fields: %s", event)
        return

    from app.core.database import SessionLocal
    from app.modules.chat.models import ChatRoom

    db = SessionLocal()
    try:
        existing = db.query(ChatRoom).filter(ChatRoom.request_id == request_id).first()
        if not existing:
            room = ChatRoom(
                request_id=request_id,
                donor_user_id=donor_user_id,
                patient_user_id=patient_user_id,
            )
            db.add(room)
            db.commit()
            logger.info("✅ Auto-created chat room for request #%s", request_id)

            # Send push notification to both parties
            try:
                import httpx
                room_id = room.id
                for user_id in [donor_user_id, patient_user_id]:
                    httpx.post(
                        f"{settings.NTFY_BASE_URL}/{settings.NTFY_TOPIC_PREFIX}-{user_id}",
                        content=f"Your chat room is ready! Open the app to start messaging.",
                        headers={"Title": "💬 Chat Room Ready", "Tags": "speech_balloon"},
                        timeout=5.0,
                    )
            except Exception as e:
                logger.warning("Chat room notification failed: %s", e)
        else:
            logger.debug("Chat room already exists for request #%s", request_id)
    except Exception as exc:
        db.rollback()
        logger.warning("Error creating chat room: %s", exc)
    finally:
        db.close()


async def start_consumer() -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        queue = await channel.declare_queue("chat-service.blood-request-accepted", durable=True)
        await queue.bind(exchange, routing_key="blood_request.accepted")

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    event = json.loads(message.body.decode())
                    await handle_blood_request_accepted(event)
                except Exception as exc:
                    logger.warning("Error processing chat event: %s", exc)

        await queue.consume(on_message)
        logger.info("✅ chat-service consumer started")
    except Exception as exc:
        logger.warning("⚠️ chat-service consumer failed: %s", exc)
