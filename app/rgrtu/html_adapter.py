from __future__ import annotations

import httpx

from app.config import Settings


class RgrtuHtmlAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.rgrtu_verify_ssl,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
