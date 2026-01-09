import aio_pika
from app.core.config import settings

connection = None
channel = None

async def connect():
    global connection, channel

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    channel = await connection.channel()

    await channel.set_qos(prefetch_count=10)

async def disconnect():
    if connection:
        await connection.close()