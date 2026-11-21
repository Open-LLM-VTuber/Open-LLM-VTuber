"""Optional shared PostgreSQL pool and best-effort Redis cache."""
import os
import threading
from contextlib import contextmanager
from functools import lru_cache

_lock = threading.Lock()
_pool = None


@contextmanager
def postgres_connection():
    global _pool
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
    with _lock:
        if _pool is None:
            _pool = ConnectionPool(os.environ['VTUBER_DATABASE_URL'], min_size=1, max_size=8,
                                   timeout=3, kwargs={'row_factory': dict_row})
    with _pool.connection() as connection:
        yield connection


class PgAdapter:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, args=()):
        if sql == 'BEGIN IMMEDIATE':
            # Serialize version allocation within the short memory write transaction.
            return self.connection.execute('LOCK TABLE memories IN SHARE ROW EXCLUSIVE MODE')
        return self.connection.execute(sql.replace('?', '%s'), args)


@lru_cache(maxsize=1)
def redis_client():
    url = os.environ.get('VTUBER_REDIS_URL')
    if not url:
        return None
    from redis import Redis
    return Redis.from_url(url, socket_connect_timeout=.2, socket_timeout=.2,
                          decode_responses=True)


def cache_get(key):
    try:
        client = redis_client()
        return client.get('vtuber:v1:' + key) if client else None
    except Exception:
        return None


def cache_put(key, value, ttl=2):
    try:
        client = redis_client()
        if client:
            client.setex('vtuber:v1:' + key, ttl, value)
    except Exception:
        pass
