import socket
import time
import redis
from datetime import datetime, timedelta
from Config.config import AppConfig

class SessionManager:
    def __init__(self):
        self.redis = None
        self._connect_with_retry()

    def _connect_with_retry(self, max_attempts=10, delay=3):
        """Connect to Redis using Docker's internal DNS"""
        for attempt in range(max_attempts):
            try:
                self.redis = redis.Redis(
                    host='redis',
                    port=6379,
                    socket_connect_timeout=10,
                    socket_timeout=10,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                if self.redis.ping():
                    print("✅ Successfully connected to Redis")
                    return
            except redis.ConnectionError as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Could not connect to Redis after {max_attempts} attempts")
                time.sleep(delay * (attempt + 1))

    def create_session(self, user_id: str, role: str, expires_in: int = 3600) -> str:
        session_id = f"session:{user_id}:{int(datetime.now().timestamp())}"
        session_data = {
            "user_id": user_id,
            "role": role,
            "is_active": "true"
        }
        self.redis.hmset(session_id, session_data)
        self.redis.expire(session_id, expires_in)
        return session_id

    def validate_session(self, session_id: str) -> dict:
        if not self.redis.exists(session_id):
            return None
        return self.redis.hgetall(session_id)

    def invalidate_session(self, session_id: str) -> None:
        self.redis.delete(session_id)