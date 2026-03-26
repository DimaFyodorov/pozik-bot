"""DeepSeek API client."""

import logging

from openai import AsyncOpenAI

from .base import AIModel

logger = logging.getLogger(__name__)


class DeepSeekModel(AIModel):
    """DeepSeek model for text generation."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com',
            timeout=25.0,
        )
        self.model = model

    async def generate(
        self,
        prompt: str,
        context: str = '',
        system_prompt: str = '',
        image_path: str | None = None,
    ) -> str:
        """Generate text response."""
        if image_path:
            logger.warning('DeepSeek does not support images')
            return 'DeepSeek не работает с изображениями.'

        messages = [
            {
                'role': 'system',
                'content': system_prompt or 'Ты полезный ассистент.',
            },
            {'role': 'user', 'content': f'{context}\n{prompt}'.strip()},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content or 'Нет ответа'
        except Exception as e:
            logger.exception('DeepSeek API error: %s', e)
            raise
