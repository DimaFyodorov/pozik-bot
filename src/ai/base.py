"""Base interface for AI models."""

from abc import ABC, abstractmethod


class AIModel(ABC):
    """Abstract base class for AI model implementations."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: str = '',
        system_prompt: str = '',
        image_path: str | None = None,
    ) -> str:
        """Generate response from AI model."""
