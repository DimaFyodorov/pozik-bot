"""Message handlers."""

import logging
from pathlib import Path

from telethon import events

from ai.router import Router
from core.access import AccessControl
from core.anti_spam import AntiSpam
from core.config import settings
from core.context import ContextManager
from core.prompts import Prompts
from core.search import SearchEngine

from .commands import CommandProcessor

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Handle incoming messages."""

    def __init__(
        self,
        client,
        router: Router,
        context_manager: ContextManager,
        access: AccessControl,
        anti_spam: AntiSpam,
        search: SearchEngine,
    ) -> None:
        self.client = client
        self.router = router
        self.context_manager = context_manager
        self.access = access
        self.anti_spam = anti_spam
        self.search = search
        self.commands = CommandProcessor(
            access=access,
            router=router,
            context_manager=context_manager,
            admin_id=access.admin_id,
        )
        self.bot_name = settings.bot_name

    async def _download_media(
        self, event: events.NewMessage.Event
    ) -> str | None:
        """Download media or extract text from files."""
        if not event.media:
            return None

        msg = event.message
        if not msg.media:
            reply = await event.get_reply_message()
            if reply and reply.media:
                msg = reply

        try:
            path = await msg.download_media(file='data/media/')
            logger.info('Downloaded media: %s', path)

            # Обработка .txt файлов
            if path and path.endswith('.txt'):
                try:
                    text = Path(path).read_text(encoding='utf-8')
                    # Возвращаем текст вместо пути, чтобы он ушёл в промпт
                    return f'📄 [TXT Файл]:\n{text[:2000]}'
                except Exception as e:
                    logger.warning('Failed to read txt: %s', e)
                    return path

            return path
        except Exception as e:
            logger.exception('Media download failed: %s', e)
            return None

    async def _should_respond(
        self, text: str, event: events.NewMessage.Event
    ) -> bool:
        """Check if bot should respond."""
        text_lower = text.lower()

        if self.bot_name in text_lower:
            return True

        # No need
        # if event.is_reply:
        #     reply = await event.get_reply_message()
        #     if reply and reply.sender_id == (await self.client.get_me()).id:
        #         return True

        return False

    async def handle_message(self, event: events.NewMessage.Event) -> None:
        """Main message handler."""
        text = event.raw_text or ''
        chat_id = event.chat_id
        user_id = event.sender_id

        # Process commands
        if text.startswith('!'):
            result = await self.commands.process(event, text)
            if result:
                response, delete = result
                # HTML formatting for all command replies
                await event.reply(response, parse_mode='HTML')
                if delete:
                    await event.delete()
                return

        # Check if bot is enabled in chat
        if not self.access.is_enabled(chat_id):
            return

        # Check ban
        if self.access.is_banned(user_id):
            logger.debug('Banned user %s in chat %s', user_id, chat_id)
            return

        # Anti-spam
        if not self.anti_spam.allow(user_id):
            logger.debug('Rate limited user %s', user_id)
            return

        # Get sender info
        sender = await event.get_sender()
        username = sender.username or sender.first_name or str(user_id)

        # Add to context
        ctx = self.context_manager.get(chat_id)
        ctx.add(username, text)

        # Check if should respond
        if not await self._should_respond(text, event):
            return

        # Download media
        image_path = await self._download_media(event)

        # Search if triggered
        search_results = await self.search.search(text)
        search_context = ''
        if search_results:
            search_context = self.search.format_results(search_results)

        # Build prompt
        context = self.context_manager.get_formatted(chat_id)

        # Get style from context manager
        style = self.context_manager.get_system_prompt_mode(chat_id)
        system_prompt = Prompts.get(style)

        try:
            response = await self.router.route(
                chat_id=chat_id,
                prompt=text.replace(self.bot_name, '').strip(),
                context=context + '\n' + search_context
                if search_context
                else context,
                system_prompt=system_prompt,
                image_path=image_path,
            )

            # HTML formatting for ALL bot replies
            await event.reply(response, parse_mode='HTML')
            ctx.add('Позик', response)

            # Compress context if needed
            await self.context_manager.compress_if_needed(chat_id)

        except Exception as e:
            logger.exception('Generation failed: %s', e)
            await event.reply(
                '❌ <b>Ошибка:</b> Произошла ошибка при генерации ответа.',
                parse_mode='HTML',
            )

        # Cleanup media
        if image_path and Path(image_path).exists():
            Path(image_path).unlink()


def register_handlers(client, handlers: MessageHandlers) -> None:
    """Register all handlers."""

    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        await handlers.handle_message(event)

    logger.info('Handlers registered')
