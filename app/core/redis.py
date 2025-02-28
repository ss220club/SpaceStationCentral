import redis.asyncio as redis

from app.core.config import CONFIG

REDIS_POOL = redis.ConnectionPool.from_url(CONFIG.redis.connection_string)


async def send_message(channel: str, message: str) -> None:
    client = redis.Redis(connection_pool=REDIS_POOL)
    await client.publish(f"{CONFIG.redis.channel}.{channel}", message)
