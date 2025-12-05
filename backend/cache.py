import json
from typing import Optional
import redis


class CacheClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: str = None):
        self.client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)

    def get_json(self, key: str) -> Optional[dict]:
        data = self.client.get(key)
        if not data:
            return None
        return json.loads(data)

    def set_json(self, key: str, value: dict, expire_seconds: int = 3600):
        self.client.set(key, json.dumps(value, ensure_ascii=False), ex=expire_seconds)
