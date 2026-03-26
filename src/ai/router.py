"""Model routing logic."""

import logging
from enum import StrEnum

from .base import AIModel
from .deepseek import DeepSeekModel
from .gemini import GeminiModel

logger = logging.getLogger(__name__)


class ModelMode(StrEnum):
    """Available model modes."""

    DEEPSEEK = 'deepseek'
    GEMINI = 'gemini'
    HYBRID = 'hybrid'


class Router:
    """Route requests to appropriate AI model."""

    def __init__(self, deepseek: DeepSeekModel, gemini: GeminiModel) -> None:
        self.deepseek = deepseek
        self.gemini = gemini
        self._model_modes: dict[int, ModelMode] = {}

    def set_mode(self, chat_id: int, mode: ModelMode) -> None:
        """Set model mode for chat."""
        self._model_modes[chat_id] = mode
        logger.info('Model mode set to %s for chat %s', mode, chat_id)

    def get_mode(self, chat_id: int) -> ModelMode:
        """Get model mode for chat."""
        return self._model_modes.get(chat_id, ModelMode.HYBRID)

    async def _safe_generate(self, model: AIModel, *args, **kwargs) -> str:
        """Generate with fallback."""
        try:
            return await model.generate(*args, **kwargs)
        except Exception as e:
            logger.exception('Model generation failed: %s', e)
            raise

    async def route(
        self,
        chat_id: int,
        prompt: str,
        context: str = '',
        system_prompt: str = '',
        image_path: str | None = None,
    ) -> str:
        """Route to appropriate model based on mode and content."""
        mode = self.get_mode(chat_id)

        # Hybrid: image → Gemini, text → DeepSeek
        if mode == ModelMode.HYBRID:
            if image_path:
                return await self._safe_generate(
                    self.gemini, prompt, context, system_prompt, image_path
                )
            return await self._safe_generate(
                self.deepseek, prompt, context, system_prompt
            )

        if mode == ModelMode.DEEPSEEK:
            return await self._safe_generate(
                self.deepseek, prompt, context, system_prompt
            )

        if mode == ModelMode.GEMINI:
            return await self._safe_generate(
                self.gemini, prompt, context, system_prompt, image_path
            )

        # Fallback to Gemini on error
        logger.warning('All models failed, using Gemini fallback')
        return await self.gemini.generate(
            prompt, context, system_prompt, image_path
        )
