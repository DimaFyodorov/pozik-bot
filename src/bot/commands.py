"""Command processing."""

import logging

from telethon import events

from ai.router import ModelMode, Router
from core.access import AccessControl
from core.context import ContextManager
from core.prompts import Prompts

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Process bot commands."""

    def __init__(
        self,
        access: AccessControl,
        router: Router,
        context_manager: ContextManager,
        admin_id: int,
    ) -> None:
        self.access = access
        self.router = router
        self.context_manager = context_manager
        self.admin_id = admin_id

    def _check_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.admin_id

    async def process(
        self,
        event: events.NewMessage.Event,
        text: str,
    ) -> tuple[str, bool] | None:
        """Process command and return (response, delete_after)."""
        if not text.startswith('!'):
            return None

        parts = text.split()
        cmd = parts[0].lower()

        handlers = {
            '!pozik': self._handle_pozik,
            '!ban': self._handle_ban,
            '!unban': self._handle_unban,
            '!mode': self._handle_mode,
            '!style': self._handle_style,
            '!help': self._handle_help,
            '!summary': self._handle_summary,
        }

        handler = handlers.get(cmd)
        if handler:
            return await handler(event, parts)

        return None

    async def _handle_pozik(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !pozik on/off."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        if len(parts) < 2:
            return ('❗ <b>Использование:</b> <code>!pozik on|off</code>', True)

        chat_id = event.chat_id
        chat = await event.get_chat()
        chat_name = getattr(chat, 'title', None) or str(chat_id)

        if parts[1].lower() == 'on':
            self.access.enable(chat_id)
            return (
                f'✅ <b>Бот включён</b> в чате <code>{chat_name}</code>',
                True,
            )

        if parts[1].lower() == 'off':
            self.access.disable(chat_id)
            return (
                f'⛔ <b>Бот выключен</b> в чате <code>{chat_name}</code>',
                True,
            )

        return ('❗ <b>Использование:</b> <code>!pozik on|off</code>', True)

    async def _handle_ban(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !ban @username."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        if len(parts) < 2:
            return (
                '❗ <b>Использование:</b> <code>!ban @username</code>',
                True,
            )

        username = parts[1].lstrip('@')
        try:
            entity = await event.client.get_entity(username)
            self.access.ban(entity.id, username)
            return (
                f'🔨 <b>Пользователь</b> <code>@{username}</code> <b>забанен</b>',
                True,
            )
        except Exception as e:
            logger.exception('Ban failed: %s', e)
            return (f'❌ <b>Ошибка:</b> <code>{e}</code>', True)

    async def _handle_unban(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !unban @username."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        if len(parts) < 2:
            return (
                '❗ <b>Использование:</b> <code>!unban @username</code>',
                True,
            )

        username = parts[1].lstrip('@')
        try:
            entity = await event.client.get_entity(username)
            self.access.unban(entity.id, username)
            return (
                f'✅ <b>Пользователь</b> <code>@{username}</code> <b>разбанен</b>',
                True,
            )
        except Exception as e:
            logger.exception('Unban failed: %s', e)
            return (f'❌ <b>Ошибка:</b> <code>{e}</code>', True)

    async def _handle_mode(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !mode deepseek|gemini|hybrid."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        if len(parts) < 2:
            modes = ', '.join([f'<code>{m.value}</code>' for m in ModelMode])
            return (
                f'❗ <b>Использование:</b> <code>!mode [{modes}]</code>',
                True,
            )

        try:
            mode = ModelMode(parts[1].lower())
            self.router.set_mode(event.chat_id, mode)
            return (f'🔄 <b>Режим модели:</b> <code>{mode.value}</code>', True)
        except ValueError:
            modes = ', '.join([f'<code>{m.value}</code>' for m in ModelMode])
            return (f'❗ <b>Доступные режимы:</b> <code>{modes}</code>', True)

    async def _handle_style(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !style normal|toxic."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        if len(parts) < 2:
            return (
                '❗ <b>Использование:</b> <code>!style [normal|toxic]</code>',
                True,
            )

        style = parts[1].lower()
        if style not in ('normal', 'toxic'):
            return (
                '❗ <b>Доступные стили:</b> <code>normal</code>, <code>toxic</code>',
                True,
            )

        self.context_manager.set_system_prompt_mode(event.chat_id, style)
        return (f'🎭 <b>Стиль установлен:</b> <code>{style}</code>', True)

    async def _handle_summary(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !summary command."""
        if not self._check_admin(event.sender_id):
            return ('❌ <b>Доступ запрещён</b>', True)

        chat_id = event.chat_id
        ctx = self.context_manager.get(chat_id)

        if not ctx.messages:
            return ('❗ <b>Контекст пуст</b>', True)

        try:
            summary = await self.router.route(
                chat_id=chat_id,
                prompt='Сделай краткое резюме этого чата',
                context=ctx.get_formatted(),
                system_prompt=Prompts.get('summary'),
            )
            return (
                f'📝 <b>Резюме чата:</b>\n<code>{summary[:4000]}</code>',
                False,
            )
        except Exception as e:
            logger.exception('Summary failed: %s', e)
            return (f'❌ <b>Ошибка:</b> <code>{e}</code>', True)

    async def _handle_help(
        self,
        event: events.NewMessage.Event,
        parts: list[str],
    ) -> tuple[str, bool] | None:
        """Handle !help command."""
        help_text = (
            '🤖 <b>Позик — AI Помощник</b>\n\n'
            '<b>Команды администратора:</b>\n'
            '<code>!pozik on</code> — включить бота в чате\n'
            '<code>!pozik off</code> — выключить бота в чате\n'
            '<code>!summary</code> — составляет резюме по чату\n'
            '<code>!mode [mode]</code> — режим модели (deepseek/gemini/hybrid)\n'
            '<code>!style [style]</code> — стиль общения (normal/toxic)\n'
            '<code>!ban @user</code> — забанить пользователя\n'
            '<code>!unban @user</code> — разбанить пользователя\n'
            '<code>!help</code> — показать эту справку\n\n'
            '<b>Режимы моделей:</b>\n'
            '• <code>deepseek</code> — только текст, быстро\n'
            '• <code>gemini</code> — текст + картинки\n'
            '• <code>hybrid</code> — автовыбор (текст→DeepSeek, фото→Gemini)\n\n'
            '<b>Стили общения:</b>\n'
            '• <code>normal</code> — вежливый помощник\n'
            '• <code>toxic</code> — режим «Нейрохам»\n\n'
            '<i>Бот отвечает только при упоминании имени.</i>'
        )
        return (help_text, False)
