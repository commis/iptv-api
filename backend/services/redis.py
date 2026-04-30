from typing import Optional

from core.logger_factory import LoggerFactory
from services.config import config_manager

try:
    import redis
except ImportError:
    redis = None

logger = LoggerFactory.get_logger(__name__)


class RedisClient:

    def __init__(self):
        self._client = None

    def _init_client(self):
        if self._client is not None:
            return

        if redis is None:
            logger.warning("redis library not installed, redis cache will not work")
            return

        try:
            redis_config = config_manager.redis_config
            host = redis_config.get("host")
            port = int(redis_config.get("port", "6379"))
            db = int(redis_config.get("db", "1"))
            password = redis_config.get("password")
            self._expire = redis_config.get("expire")
            self._client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        except Exception as e:
            logger.error(f"init redis client failed: {e}")
            self._client = None

    def get(self, key: str) -> Optional[str]:
        self._init_client()
        if not self._client:
            return None

        try:
            return self._client.get(key)
        except Exception as e:
            logger.warning(f"redis get failed, key={key}, error={e}")
            return None

    def set(self, key: str, value: str) -> None:
        self._init_client()
        if not self._client:
            return

        try:
            self._client.set(key, value)
        except Exception as e:
            logger.warning(f"redis set failed, key={key}, error={e}")

    def set_ex(self, key: str, value: str, ex: int = -1) -> None:
        self._init_client()
        if not self._client:
            return

        try:
            if ex == -1:
                ex = self._expire
            self._client.set(key, value, ex=ex)
        except Exception as e:
            logger.warning(f"redis set failed, key={key}, error={e}")


redis_client = RedisClient()
