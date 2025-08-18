import random
import time

import redis


class RateLimitExceed(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        name="rate_limiter",
        max_requests=5,
        window=3,
        host="localhost",
        port=6379,
        db=0,
    ):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.name = name
        self.max_requests = max_requests
        self.window = window

    def test(self) -> bool:
        now = time.time()
        self.r.zremrangebyscore(self.name, 0, now - self.window)
        requests_num = self.r.zcard(self.name)

        if requests_num >= self.max_requests:
            return False

        self.r.zadd(self.name, {str(now): now})

        return True


def make_api_request(rate_limiter: RateLimiter):
    if not rate_limiter.test():
        raise RateLimitExceed
    else:
        # какая-то бизнес логика
        pass


if __name__ == "__main__":
    rate_limiter = RateLimiter()

    for _ in range(50):
        time.sleep(random.randint(1, 2))  # случайные интервалы

        try:
            make_api_request(rate_limiter)
        except RateLimitExceed:
            print("Rate limit exceed!")
        else:
            print("All good")
