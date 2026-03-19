import os

import redis

_redis_client = None
_redis_initialized = False


def get_redis_client():
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client

    host = os.getenv("ELA_REDIS_HOST", "localhost")
    port = int(os.getenv("ELA_REDIS_PORT", "6379"))
    db_index = int(os.getenv("ELA_REDIS_DB", "0"))
    try:
        _redis_client = redis.Redis(host=host, port=port, db=db_index)
        _redis_client.ping()
    except Exception:
        _redis_client = None
    finally:
        _redis_initialized = True
    return _redis_client
