import json

import redis


class RedisQueue:
    def __init__(self, name="redis_queue", host="localhost", port=6379, db=0):
        self.name = name
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def publish(self, msg: dict) -> None:
        data = json.dumps(msg)
        self.r.rpush(self.name, data)

    def consume(self) -> dict:
        data = json.loads(self.r.lpop(self.name))
        return data if data is not None else None


if __name__ == "__main__":
    q = RedisQueue()

    q.publish({"a": 1})
    q.publish({"b": 2})
    q.publish({"c": 3})

    assert q.consume() == {"a": 1}
    assert q.consume() == {"b": 2}
    assert q.consume() == {"c": 3}
