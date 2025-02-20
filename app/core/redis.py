import redis

from app.core.config import CONFIG

REDIS = redis.from_url(CONFIG.redis.connection_string)