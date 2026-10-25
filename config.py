import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


def mask_secret(secret: str) -> str:
    """Mask secret key for safe logging (e.g. sk-or...1234)."""
    if not secret:
        return "[NOT SET]"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash").strip()
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    compression_threshold: int = int(os.getenv("COMPRESSION_THRESHOLD", "50"))
    keep_recent_messages: int = int(os.getenv("KEEP_RECENT_MESSAGES", "4"))
    max_summary_tokens: int = int(os.getenv("MAX_SUMMARY_TOKENS", "300"))
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", "2000"))
    token_trigger_threshold: int = int(os.getenv("TOKEN_TRIGGER_THRESHOLD", "8000"))
    max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "12000"))
    database_path: str = os.getenv("DATABASE_PATH", "bot_data.sqlite3").strip()

    system_instruction: str = (
        "Ти інтелектуальний помічник у Telegram. Завжди відповідай виключно українською мовою. "
        "Твої відповіді мають бути чіткими, інформативними, ввічливими та структурованими. "
        "Дотримуйся наданого контексту та підсумку попередньої розмови."
    )

    def validate(self) -> None:
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if missing:
            raise ValueError(f"Відсутні обов'язкові змінні оточення у .env: {', '.join(missing)}")


config = Config()
