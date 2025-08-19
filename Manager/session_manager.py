import redis
import socket
import time

from datetime import datetime, timedelta

from Config.config import AppConfig


class SessionManager:
    def __init__(self):
        """
        Initialize the SessionManager instance.
        Establishes connection to Redis with retry logic for containerized
        environments where Redis might not be immediately available.

        Args:
            None

        Returns:
            None
        """
        self.redis = None
        self._connect_with_retry()

    def _connect_with_retry(self, max_attempts=10, delay=3):
        """
        Establish Redis connection with exponential backoff retry logic.

        Args:
            max_attempts (int, optional): Maximum number of connection attempts.
                                         Defaults to 10.
            delay (int, optional): Base delay in seconds between attempts.
                                  Defaults to 3.

        Returns:
            None
        """
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
                    return
            except redis.ConnectionError as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(
                        f"Could not connect to Redis after {max_attempts} attempts")
                time.sleep(delay * (attempt + 1))

    def create_session(self, user_id: str, role: str, expires_in: int = 3600) -> str:
        """
        Create a new user session with automatic expiration.

        Args:
            user_id (str): Unique identifier for the user.
            role (str): User role/privilege level.
            expires_in (int, optional): Session duration in seconds.
                                       Defaults to 3600 (1 hour).

        Returns:
            str: Unique session ID in format "session:{user_id}:{timestamp}".
        """
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
        """
        Validate a session and retrieve session data.

        Args:
            session_id (str): The session ID to validate.

        Returns:
            dict: Session data containing user_id, role, and is_active,
                  or None if session doesn't exist or has expired.
        """
        if not self.redis.exists(session_id):
            return None
        return self.redis.hgetall(session_id)

    def invalidate_session(self, session_id: str) -> None:
        """
        Invalidate (delete) a session immediately.

        Args:
            session_id (str): The session ID to invalidate.

        Returns:
            None
        """
        self.redis.delete(session_id)
