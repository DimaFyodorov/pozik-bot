"""Gemini API client via OpenAI-compatible endpoint."""

import base64
import logging
from pathlib import Path

from openai import AsyncOpenAI

from .base import AIModel

logger = logging.getLogger(__name__)


class GeminiModel(AIModel):
    """Gemini model with vision capabilities."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=45.0,
        )
        self.model = model

    async def generate(
        self,
        prompt: str,
        context: str = '',
        system_prompt: str = '',
        image_path: str | None = None,
    ) -> str:
        """Generate response with optional image."""
        messages = [
            {
                'role': 'system',
                'content': system_prompt or 'Ты полезный ассистент.',
            },
        ]

        user_content = [
            {'type': 'text', 'text': f'{context}\n{prompt}'.strip()}
        ]

        if image_path and Path(image_path).exists():
            try:
                image_data = base64.b64encode(
                    Path(image_path).read_bytes()
                ).decode()
                user_content.append({
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{image_data}'
                    },
                })
            except Exception as e:
                logger.warning('Failed to load image: %s', e)

        messages.append({'role': 'user', 'content': user_content})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content or 'Нет ответа'
        except Exception as e:
            logger.exception('Gemini API error: %s', e)
            raise
