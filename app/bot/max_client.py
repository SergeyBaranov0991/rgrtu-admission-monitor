from __future__ import annotations

import httpx

from app.config import Settings


class MaxClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_message(self, user_id: str, text: str, attachments: list[dict] | None = None) -> None:
        if self.settings.max_bot_token is None:
            raise RuntimeError("MAX_BOT_TOKEN is not configured")
        token = self.settings.max_bot_token.get_secret_value()
        url = f"{self.settings.max_api_base_url.rstrip('/')}/messages"
        payload: dict = {"text": text}
        if attachments:
            payload["attachments"] = attachments
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                params={"user_id": user_id},
                headers={"Authorization": token, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()

