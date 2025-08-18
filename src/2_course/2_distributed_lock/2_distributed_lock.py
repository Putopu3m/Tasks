import datetime
import functools
import time
from uuid import uuid4

import redis

r = redis.Redis(host="localhost", port=6379, db=0)


def single(max_processing_time: datetime.timedelta):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lock_key = f"lock:{func.__name__}"
            lock_id = str(uuid4())

            acquired = r.set(
                lock_key,
                lock_id,
                nx=True,
                px=int(max_processing_time.total_seconds() * 1000),
            )

            if not acquired:
                print(f"Функция {func.__name__} уже выполняется на другом сервере.")
                return None

            try:
                return func(*args, **kwargs)
            finally:
                release_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                r.eval(release_script, 1, lock_key, lock_id)

        return wrapper

    return decorator


@single(max_processing_time=datetime.timedelta(minutes=2))
def process_transaction(minutes):
    print("Начинаем обработку транзакции...")
    time.sleep(minutes)
    print("Транзакция обработана!")
