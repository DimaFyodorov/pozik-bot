"""Configuration from environment."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Bot configuration."""

    bot_name: str = os.getenv('BOT_NAME', 'pozik').lower()

    api_id: int = int(os.getenv('API_ID', '0'))
    api_hash: str = os.getenv('API_HASH', '')
    session_path: str = os.getenv('SESSION_PATH', 'data/pozik_session')

    admin_id: int = int(os.getenv('ADMIN_ID', '0'))

    deepseek_api_key: str = os.getenv('DEEPSEEK_API_KEY', '')
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
    gemini_base_url: str = os.getenv(
        'GEMINI_BASE_URL', 'https://api.aitunnel.ru/v1/'
    )
    model_deepseek: str = 'deepseek-chat'
    model_gemini: str = 'gemini-2.5-flash'

    data_path: str = os.getenv('DATA_PATH', './data')

    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', './data/bot.log')
    log_tg_enabled: bool = (
        os.getenv('LOG_TG_ENABLED', 'false').lower() == 'true'
    )
    log_tg_token: str = os.getenv('LOG_TG_TOKEN', '')
    log_tg_chat_id: int = int(os.getenv('LOG_TG_CHAT_ID', '0'))

    context_limit: int = int(os.getenv('CONTEXT_LIMIT', '30'))
    context_keep: int = int(os.getenv('CONTEXT_KEEP', '20'))
    rate_limit_seconds: float = float(os.getenv('RATE_LIMIT_SECONDS', '3'))

    def __post_init__(self) -> None:
        """Create data directory."""
        Path(self.data_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
