import redis  # type: ignore
from redis.backoff import ExponentialBackoff  # type: ignore
from redis.exceptions import BusyLoadingError  # type: ignore
from redis.exceptions import ConnectionError, TimeoutError
from redis.retry import Retry  # type: ignore


class StorageError(Exception):
    def __init__(self, method_name, details):
        super().__init__(f"Error in {method_name}: {details}")


def storage_error_catcher(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (BusyLoadingError, ConnectionError, TimeoutError) as error:
            raise StorageError(func.__name__, str(error))

    return wrapper


class Storage:
    def __init__(
        self,
        host: str,
        port: int,
        retry_num: int = 3,
        socket_timeout: int = 10,
        socket_connect_timeout: int = 5,
    ):
        retry = Retry(ExponentialBackoff(), retry_num)

        self.store = redis.StrictRedis(
            host=host,
            port=port,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry=retry,
            retry_on_timeout=True,
            decode_responses=True,
        )

    @storage_error_catcher
    def get(self, key):
        return self.store.get(key)

    @storage_error_catcher
    def put(self, key, value):
        self.store.set(name=key, value=value)

    @storage_error_catcher
    def cache_set(self, key, value, ttl):
        self.store.set(key, value, ex=ttl)

    @storage_error_catcher
    def cache_get(self, key):
        return self.store.get(key)

    def clear(self):
        self.store.flushdb()
