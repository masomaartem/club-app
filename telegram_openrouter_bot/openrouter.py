import logging
from typing import List, Dict, Optional
import httpx
from config import config

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for mixed Ukrainian/English text.
    In multilingual BPE tokenizers (like GPT-4/Gemini), Ukrainian Cyrillic
    typically requires ~1 token per 2.5 characters or ~1.3 tokens per word.
    """
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(int(chars / 2.5), int(words * 1.3), 1)


def estimate_context_tokens(system_instruction: str, summary: str, messages: List[Dict[str, str]]) -> int:
    """Estimates the total token footprint of the payload sent to OpenRouter."""
    tokens = estimate_tokens(system_instruction)
    if summary:
        tokens += estimate_tokens(summary) + 25
    for m in messages:
        tokens += estimate_tokens(m.get("content", "")) + 5
    return tokens


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.openrouter_api_key
        self.base_url = config.openrouter_base_url.rstrip("/")
        self.model = config.openrouter_model
        self.max_summary_tokens = config.max_summary_tokens
        self.max_response_tokens = config.max_response_tokens
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/telegram-openrouter-bot",
            "X-Title": "Telegram OpenRouter Bot",
            "Content-Type": "application/json",
        }
        self.timeout = httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=15.0)

    async def generate_chat_response(
        self,
        summary: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        Generate assistant response to user messages, integrating previous summary if present.
        Never logs sensitive keys or secrets.
        """
        payload_messages: List[Dict[str, str]] = []

        # System instruction
        system_content = config.system_instruction
        if summary:
            system_content += (
                "\n\n--- ПІДСУМОК ПОПЕРЕДНЬОЇ ЧАСТИНИ РОЗМОВИ ---\n"
                f"{summary}\n"
                "-----------------------------------------------\n"
                "Використовуй цей підсумок для збереження контексту бесіди."
            )

        payload_messages.append({"role": "system", "content": system_content})

        # Add active messages
        for msg in messages:
            payload_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        body = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": 0.7,
            "max_tokens": self.max_response_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            except httpx.HTTPStatusError as e:
                err_text = ""
                try:
                    err_json = e.response.json()
                    err_text = err_json.get("error", {}).get("message", e.response.text)
                except Exception:
                    err_text = e.response.text
                logger.error("HTTP помилка OpenRouter: статус %s - %s", e.response.status_code, err_text)
                if e.response.status_code == 402:
                    return f"⚠️ Помилка OpenRouter (402: Недостатньо кредитів або ліміт токенів): {err_text}"
                return f"⚠️ Помилка сервісу OpenRouter ({e.response.status_code}). Будь ласка, спробуйте пізніше."
            except Exception as e:
                logger.error("Помилка з'єднання з OpenRouter: %s", type(e).__name__)
                return "⚠️ Не вдалося отримати відповідь від моделі. Перевірте з'єднання або API ключ."

    async def compress_context(
        self,
        previous_summary: str,
        messages_to_summarize: List[Dict[str, str]],
    ) -> Optional[str]:
        """
        Combines previous summary and older conversation history into a concise updated summary.
        If compression fails, returns None so caller can preserve history and retry later.
        """
        if not messages_to_summarize:
            return previous_summary

        dialogue_text = []
        for msg in messages_to_summarize:
            speaker = "Користувач" if msg["role"] == "user" else "Асистент"
            dialogue_text.append(f"{speaker}: {msg['content']}")
        formatted_dialogue = "\n".join(dialogue_text)

        system_prompt = (
            "Ти експерт зі стиснення контексту діалогів для оптимізації витрат токенів. "
            "Твоє завдання — створити лаконічний, компактний підсумок розмови українською мовою. "
            "Вимоги:\n"
            "1. Об'єднай попередній підсумок (якщо є) і фрагмент бесіди в один актуальний підсумок.\n"
            "2. Збережи виключно критичні факти: імена, уподобання, тему, мету розмови, узгоджені рішення та цифри.\n"
            "3. Максимальна довжина: до 150 слів. Формат: короткі тези (маркований список).\n"
            "4. Жодних вступних фраз (наприклад, 'Ось підсумок:'). Повертай тільки сам підсумок."
        )

        user_content = ""
        if previous_summary:
            user_content += f"Попередній підсумок:\n{previous_summary}\n\n"
        user_content += f"Діалог для опрацювання:\n{formatted_dialogue}\n\nСтвори оновлений короткий підсумок:"

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": self.max_summary_tokens,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(
                    "Виконується стиснення контексту (повідомлень для стиснення: %d)...",
                    len(messages_to_summarize),
                )
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                new_summary = data["choices"][0]["message"]["content"].strip()
                logger.info("Контекст успішно стиснуто. Нова довжина підсумку: %d символів", len(new_summary))
                return new_summary
            except Exception as e:
                logger.warning(
                    "Помилка під час стиснення контексту через OpenRouter (%s). Історію збережено без змін для наступної спроби.",
                    type(e).__name__,
                )
                return None
