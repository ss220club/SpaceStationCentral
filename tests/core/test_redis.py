# pyright: reportPrivateUsage = false
from unittest.mock import AsyncMock, Mock

import pytest
from app.core.redis import RedisClient
from pytest_mock import MockerFixture
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError


@pytest.fixture
def redis_client() -> RedisClient:
    return RedisClient(connection_string="redis://localhost:6379/0", channel_prefix="test")


class TestRedisClient:
    def test_init(self, redis_client: RedisClient) -> None:
        assert redis_client.connection_string == "redis://localhost:6379/0"
        assert redis_client.channel_prefix == "test"
        assert redis_client._pool is not None

    @pytest.mark.asyncio
    async def test_publish(self, redis_client: RedisClient, mocker: MockerFixture) -> None:
        context_mock = AsyncMock()
        context_mock.publish.return_value = 1

        redis_mock = AsyncMock(spec=Redis)
        redis_mock.__aenter__.return_value = context_mock

        mocker.patch.object(redis_client, "get_client", return_value=redis_mock)

        channel = "test_channel"
        message = "test_message"
        result = await redis_client.publish(channel, message)

        assert result == 1
        context_mock.publish.assert_called_once_with(f"{redis_client.channel_prefix}.{channel}", message)

    @pytest.mark.asyncio
    async def test_publish_with_error(self, redis_client: RedisClient, mocker: MockerFixture) -> None:
        context_mock = AsyncMock()
        context_mock.publish.side_effect = RedisError("Test error")

        redis_mock = AsyncMock(spec=Redis)
        redis_mock.__aenter__.return_value = context_mock

        mocker.patch.object(redis_client, "get_client", return_value=redis_mock)

        with pytest.raises(RedisError, match="Test error"):
            await redis_client.publish("channel", "message")

    @pytest.mark.asyncio
    async def test_subscribe(self, redis_client: RedisClient, mocker: MockerFixture) -> None:
        pubsub_mock = AsyncMock(spec=PubSub)

        redis_mock = AsyncMock(spec=Redis)
        redis_mock.pubsub.return_value = pubsub_mock

        mocker.patch.object(redis_client, "get_client", return_value=redis_mock)

        channel = "test_channel"
        result = await redis_client.subscribe(channel)

        assert result is pubsub_mock
        pubsub_mock.subscribe.assert_called_once_with(f"{redis_client.channel_prefix}.{channel}")

    @pytest.mark.asyncio
    async def test_subscribe_with_error(self, redis_client: RedisClient, mocker: MockerFixture) -> None:
        pubsub_mock = AsyncMock(spec=PubSub)
        pubsub_mock.subscribe.side_effect = RedisError("Redis connection failed")

        redis_mock = AsyncMock(spec=Redis)
        redis_mock.pubsub.return_value = pubsub_mock

        mocker.patch.object(redis_client, "get_client", return_value=redis_mock)

        with pytest.raises(RedisError, match="Redis connection failed"):
            await redis_client.subscribe("test_channel")

    @pytest.mark.asyncio
    async def test_close(self, redis_client: RedisClient) -> None:
        redis_client._pool = Mock(spec=ConnectionPool)
        redis_client._pool.disconnect = AsyncMock()

        await redis_client.close()

        redis_client._pool.disconnect.assert_called_once()
