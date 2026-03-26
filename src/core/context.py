"""Chat context management with persistence."""

import asyncio
import json
import logging
from collections import deque
from pathlib import Path

from .prompts import Prompts

logger = logging.getLogger(__name__)


class ChatContext:
    """Context for a single chat."""

    def __init__(self, limit: int, keep: int) -> None:
        self.limit = limit
        self.keep = keep
        self.messages: deque = deque(maxlen=limit)
        self.summary: str = ''
        self.system_prompt_mode: str = 'normal'

    def add(self, username: str, text: str) -> bool:
        """Add message, return True if compression needed."""
        self.messages.append(f'{username}: {text}')
        return len(self.messages) >= self.limit

    def compress(self, old_messages: list[str]) -> None:
        """Move old messages to summary."""
        while len(self.messages) > self.keep and old_messages:
            if old_messages:
                self.summary += '\n' + old_messages.pop(0)

    def get_formatted(self) -> str:
        """Get formatted context."""
        parts = []
        if self.summary:
            parts.append(f'📝 История:\n{self.summary}')
        if self.messages:
            parts.append('📌 Последние:\n' + '\n'.join(self.messages))
        return '\n'.join(parts)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            'summary': self.summary,
            'messages': list(self.messages),
            'system_prompt_mode': self.system_prompt_mode,
        }

    @classmethod
    def from_dict(cls, data: dict, limit: int, keep: int) -> 'ChatContext':
        """Deserialize from dict."""
        ctx = cls(limit, keep)
        ctx.summary = data.get('summary', '')
        ctx.system_prompt_mode = data.get('system_prompt_mode', 'normal')
        for msg in data.get('messages', []):
            ctx.messages.append(msg)
        return ctx


class ContextManager:
    """Manage contexts for all chats."""

    def __init__(
        self,
        router,
        limit: int,
        keep: int,
        data_path: str,
    ) -> None:
        self.router = router
        self.limit = limit
        self.keep = keep
        self.data_path = Path(data_path)
        self.context_file = self.data_path / 'context.json'
        self.contexts: dict[int, ChatContext] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        """Load contexts from disk (sync)."""
        if not self.context_file.exists():
            logger.info('No context file found, starting fresh')
            return
        try:
            with Path(self.context_file).open('r', encoding='utf-8') as f:
                data = json.load(f)
            for chat_id_str, chat_data in data.items():
                chat_id = int(chat_id_str)
                self.contexts[chat_id] = ChatContext.from_dict(
                    chat_data, self.limit, self.keep
                )
            logger.info('Loaded %d contexts from disk', len(self.contexts))
        except Exception as e:
            logger.exception('Failed to load contexts: %s', e)

    def _save(self) -> None:
        """Save contexts to disk (sync)."""
        try:
            self.data_path.mkdir(parents=True, exist_ok=True)
            data = {}
            for chat_id, ctx in self.contexts.items():
                data[str(chat_id)] = ctx.to_dict()
            with Path(self.context_file).open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug('Contexts saved to disk')
        except Exception as e:
            logger.exception('Failed to save contexts: %s', e)

    async def save_async(self) -> None:
        """Save contexts asynchronously with lock."""
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._save)

    def get(self, chat_id: int) -> ChatContext:
        """Get or create context for chat."""
        if chat_id not in self.contexts:
            self.contexts[chat_id] = ChatContext(self.limit, self.keep)
        return self.contexts[chat_id]

    def get_formatted(self, chat_id: int) -> str:
        """Get formatted context for chat."""
        ctx = self.get(chat_id)
        return ctx.get_formatted()

    def set_system_prompt_mode(self, chat_id: int, mode: str) -> None:
        """Set system prompt mode for chat."""
        ctx = self.get(chat_id)
        ctx.system_prompt_mode = mode
        logger.info('System prompt mode set to %s for chat %s', mode, chat_id)

    def get_system_prompt_mode(self, chat_id: int) -> str:
        """Get system prompt mode for chat."""
        ctx = self.get(chat_id)
        return ctx.system_prompt_mode

    async def compress_if_needed(self, chat_id: int) -> None:
        """Compress context if limit exceeded."""
        ctx = self.get(chat_id)
        if len(ctx.messages) >= self.limit:
            old_messages = []
            while len(ctx.messages) > self.keep:
                old_messages.append(ctx.messages.popleft())

            if old_messages:
                try:
                    prompt = (
                        f'Текущее резюме: {ctx.summary}\nНовые сообщения:\n'
                        + '\n'.join(old_messages)
                    )
                    summary = await self.router.route(
                        chat_id=chat_id,
                        prompt=prompt,
                        context='',
                        system_prompt=Prompts.get('summary'),
                    )
                    ctx.summary = summary[:2000]
                    logger.info('Compressed context for chat %s', chat_id)
                except Exception as e:
                    logger.exception('Compression failed: %s', e)

            await self.save_async()

    async def shutdown(self) -> None:
        """Save all contexts on shutdown."""
        logger.info('Saving all contexts on shutdown...')
        await self.save_async()
