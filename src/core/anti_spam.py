"""Rate limiting."""

import logging
import time

logger = logging.getLogger(__name__)


class AntiSpam:
    """Prevent message spam."""

    def __init__(self, cooldown: float = 3.0) -> None:
        self.cooldown = cooldown
        self.last_message: dict[int, float] = {}

    def allow(self, user_id: int) -> bool:
        """Check if user can send message."""
        now = time.time()
        last = self.last_message.get(user_id, 0)

        if now - last < self.cooldown:
            return False

        self.last_message[user_id] = now
        return True
