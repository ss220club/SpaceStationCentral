# pyright: reportUnknownMemberType = false
import logging
from functools import lru_cache

from redis import RedisError
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.client import PubSub

from app.core.config import get_config


class RedisClient:
    """
    A Redis client for interacting with Redis server.

    Provides methods for common operations like publishing messages and
    handling pub/sub operations with proper connection management.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, connection_string: str, channel_prefix: str | None = None) -> None:
        """
        Initialize a Redis client with the given connection string.

        Args:
            connection_string: Redis connection URI (redis://host:port/db)
            channel_prefix: Prefix to use for all channel names (default: None)
        """
        self.connection_string = connection_string
        self.channel_prefix = channel_prefix
        self._pool: ConnectionPool = ConnectionPool.from_url(connection_string)

    def get_client(self) -> Redis:
        """
        Get a Redis client from the connection pool.

        Returns:
            Redis client instance
        """
        return Redis(connection_pool=self._pool)

    def get_full_channel_name(self, channel: str) -> str:
        """
        Get the full channel name with prefix if configured.

        Args:
            channel: Base channel name

        Returns:
            Full channel name with prefix
        """
        return f"{self.channel_prefix}.{channel}" if self.channel_prefix else channel

    async def publish(self, channel: str, message: str) -> int:
        """
        Publish a message to a channel.

        Args:
            channel: Channel to publish to
            message: Message to publish

        Returns:
            Number of clients that received the message

        Raises:
            RedisError: If there's an issue with Redis communication
        """
        try:
            async with self.get_client() as client:
                return await client.publish(self.get_full_channel_name(channel), message)
        except RedisError as e:
            self.logger.error(f"Failed to publish to Redis channel {channel}: {e}")
            raise

    async def subscribe(self, *channels: str) -> PubSub:
        """
        Subscribe to one or more channels.

        Args:
            *channels: Channels to subscribe to

        Returns:
            PubSub connection for receiving messages

        Raises:
            RedisError: If there's an issue with Redis communication
        """
        try:
            client = self.get_client()
            pubsub = client.pubsub()

            # Apply channel prefix to all channels
            full_channels = [self.get_full_channel_name(channel) for channel in channels]
            await pubsub.subscribe(*full_channels)

            return pubsub
        except RedisError as e:
            self.logger.error(f"Failed to subscribe to Redis channels {channels}: {e}")
            raise

    async def close(self) -> None:
        """Close the connection pool."""
        await self._pool.disconnect()


@lru_cache(maxsize=1)
def default_client() -> RedisClient:
    return RedisClient(
        connection_string=get_config().redis.connection_string, channel_prefix=get_config().redis.channel
    )
