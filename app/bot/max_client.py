from __future__ import annotations

import httpx

from app.bot.keyboards import max_status_keyboard
from app.config import Settings


class MaxClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_message(self, user_id: str, text: str, attachments: list[dict] | None = None) -> None:
        if self.settings.max_bot_token is None:
            raise RuntimeError("MAX_BOT_TOKEN is not configured")
        token = self.settings.max_bot_token.get_secret_value()
        url = f"{self.settings.max_api_base_url.rstrip('/')}/messages"
        chunks = _chunks(text)
        async with httpx.AsyncClient(timeout=20) as client:
            for index, chunk in enumerate(chunks):
                payload: dict = {"text": chunk}
                if index == len(chunks) - 1:
                    payload["attachments"] = attachments if attachments is not None else [max_status_keyboard()]
                response = await client.post(
                    url,
                    params={"user_id": user_id},
                    headers={"Authorization": token, "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()


def _chunks(text: str, limit: int = 3500) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = text
    while len(current) > limit:
        split_at = current.rfind("\n\n", 0, limit)
        if split_at < 1:
            split_at = current.rfind("\n", 0, limit)
        if split_at < 1:
            split_at = limit
        chunks.append(current[:split_at].strip())
        current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks
