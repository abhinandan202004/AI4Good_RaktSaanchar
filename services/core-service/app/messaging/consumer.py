"""
RabbitMQ Consumer — core-service
Consumes user.registered events to cache user info locally.
"""
import json
import logging
import asyncio

import aio_pika

from app.core.config import settings

logger = logging.getLogger(__name__)
EXCHANGE_NAME = "raktsaanchar"


async def handle_user_registered(event: dict, db_session_factory) -> None:
    """
    Cache basic user info in core schema users table.
    This allows core-service to do FK lookups without calling auth-service.
    """
    from app.modules.users.models import User, UserRole
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        user_id = event.get("user_id")
        if not user_id:
            return

        existing = db.query(User).filter(User.id == user_id).first()
        if existing:
            # Update if needed
            existing.email = event.get("email", existing.email)
            existing.phone = event.get("phone", existing.phone)
            existing.full_name = event.get("full_name", existing.full_name)
            db.commit()
            logger.info("Updated cached user %s in core schema", user_id)
        else:
            role_str = event.get("role", "donor")
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.donor

            user = User(
                id=user_id,
                email=event.get("email", ""),
                phone=event.get("phone"),
                full_name=event.get("full_name", ""),
                role=role,
                hashed_password="__cached__",  # Not used for auth in core-service
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            logger.info("Cached new user %s in core schema", user_id)
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to cache user.registered event: %s", exc)
    finally:
        db.close()


async def start_consumer() -> None:
    """Start consuming messages from RabbitMQ. Called on app startup."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        queue = await channel.declare_queue(
            "core-service.user-registered", durable=True
        )
        await queue.bind(exchange, routing_key="user.registered")

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    event = json.loads(message.body.decode())
                    await handle_user_registered(event, None)
                except Exception as exc:
                    logger.warning("Error processing message: %s", exc)

        await queue.consume(on_message)
        logger.info("✅ core-service RabbitMQ consumer started")

    except Exception as exc:
        logger.warning("⚠️ RabbitMQ consumer failed to start: %s", exc)
