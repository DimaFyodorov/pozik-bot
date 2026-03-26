"""Access control - bans and enabled chats."""

import logging

from .storage import JsonStore

logger = logging.getLogger(__name__)


class AccessControl:
    """Manage bans and enabled chats."""

    def __init__(
        self, enabled_store: JsonStore, banned_store: JsonStore
    ) -> None:
        self.enabled_store = enabled_store
        self.banned_store = banned_store
        self.admin_id = int(__import__('os').getenv('ADMIN_ID', '0'))

        # Load from storage
        enabled_data = enabled_store.load() or []
        self.enabled_chats: set[int] = (
            set(enabled_data) if isinstance(enabled_data, list) else set()
        )

        banned_data = banned_store.load() or []
        self.banned_users: dict[int, str] = {}  # user_id -> username
        if isinstance(banned_data, list):
            for item in banned_data:
                if isinstance(item, int):
                    self.banned_users[item] = 'unknown'
                elif isinstance(item, dict):
                    self.banned_users[item.get('id', 0)] = item.get(
                        'username', 'unknown'
                    )

    def is_enabled(self, chat_id: int) -> bool:
        """Check if bot is enabled in chat."""
        return chat_id in self.enabled_chats

    def enable(self, chat_id: int) -> None:
        """Enable bot in chat."""
        self.enabled_chats.add(chat_id)
        self.enabled_store.save(list(self.enabled_chats))
        logger.info('Enabled chat %s', chat_id)

    def disable(self, chat_id: int) -> None:
        """Disable bot in chat."""
        self.enabled_chats.discard(chat_id)
        self.enabled_store.save(list(self.enabled_chats))
        logger.info('Disabled chat %s', chat_id)

    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        return user_id in self.banned_users

    def ban(self, user_id: int, username: str = 'unknown') -> None:
        """Ban user."""
        self.banned_users[user_id] = username
        data = [
            {'id': uid, 'username': name}
            for uid, name in self.banned_users.items()
        ]
        self.banned_store.save(data)
        logger.info('Banned user %s (@%s)', user_id, username)

    def unban(self, user_id: int, username: str = 'unknown') -> None:
        """Unban user."""
        self.banned_users.pop(user_id, None)
        data = [
            {'id': uid, 'username': name}
            for uid, name in self.banned_users.items()
        ]
        self.banned_store.save(data)
        logger.info('Unbanned user %s (@%s)', user_id, username)
