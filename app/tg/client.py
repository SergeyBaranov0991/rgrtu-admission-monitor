from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.bot.keyboards import telegram_status_reply_markup
from app.config import Settings


@dataclass(frozen=True)
class TelegramIncomingMessage:
    update_id: int
    chat_id: str
    text: str


class TelegramClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.telegram_bot_token is None:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        self._token = settings.telegram_bot_token.get_secret_value()
        self._base_url = f"{settings.telegram_api_base_url.rstrip('/')}/bot{self._token}"

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> None:
        await self._post(
            "deleteWebhook",
            {"drop_pending_updates": drop_pending_updates},
        )

    async def get_me(self) -> dict[str, Any]:
        return await self._post("getMe", {})

    async def get_updates(self, *, offset: int | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": self.settings.telegram_poll_timeout_seconds,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        return await self._post("getUpdates", payload)

    async def send_message(self, chat_id: str, text: str, *, with_keyboard: bool = True) -> None:
        for chunk in _chunks(text):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if with_keyboard:
                payload["reply_markup"] = telegram_status_reply_markup()
            await self._post("sendMessage", payload)

    async def _post(self, method: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.settings.telegram_poll_timeout_seconds + 10) as client:
            response = await client.post(f"{self._base_url}/{method}", json=payload)
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            description = body.get("description", "Telegram API request failed")
            raise RuntimeError(f"{method}: {description}")
        return body.get("result")


def extract_message(update: dict[str, Any]) -> TelegramIncomingMessage | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    chat = message.get("chat")
    update_id = update.get("update_id")
    if not isinstance(text, str) or not isinstance(chat, dict) or update_id is None:
        return None
    chat_id = chat.get("id")
    if chat_id is None:
        return None
    return TelegramIncomingMessage(update_id=int(update_id), chat_id=str(chat_id), text=text)


def normalize_command(text: str) -> str:
    first, separator, rest = text.strip().partition(" ")
    if first.startswith("/") and "@" in first:
        first = first.split("@", 1)[0]
    return f"{first}{separator}{rest}".strip()


def _chunks(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = text
    while len(current) > limit:
        split_at = current.rfind("\n", 0, limit)
        if split_at < 1:
            split_at = limit
        chunks.append(current[:split_at].strip())
        current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks
