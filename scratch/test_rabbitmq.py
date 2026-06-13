import asyncio
import json
import os
import sys
import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://rakt:rakt@localhost:5672/")
EXCHANGE_NAME = "raktsaanchar"

async def test_publish_and_consume():
    print(f"Connecting to RabbitMQ at {RABBITMQ_URL}...")
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to RabbitMQ: {e}")
        print("\nIf you are running RabbitMQ inside Docker, start it using:")
        print("  docker compose up -d rabbitmq")
        print("\nOr check if local port 5672 is open and accessible.")
        sys.exit(1)

    print("[OK] Connected successfully!")
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )

    # Declare a test queue
    queue = await channel.declare_queue("test.integration-queue", auto_delete=True)
    await queue.bind(exchange, routing_key="test.event")

    # Publish an event
    test_payload = {"event": "test.event", "message": "Hello RaktSaanchar microservices!"}
    print(f"Publishing test event to exchange '{EXCHANGE_NAME}'...")
    await exchange.publish(
        aio_pika.Message(body=json.dumps(test_payload).encode()),
        routing_key="test.event"
    )
    print("[OK] Event published!")

    # Consume the event
    print("Waiting to receive the test event...")
    try:
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    body = json.loads(message.body.decode())
                    print(f"\n[SUCCESS] Received event: {body}")
                    break
    except Exception as e:
        print(f"[ERROR] Error during consumption: {e}")
    finally:
        await connection.close()
        print("Connection closed.")

if __name__ == "__main__":
    asyncio.run(test_publish_and_consume())
