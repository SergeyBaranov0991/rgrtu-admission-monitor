from __future__ import annotations

import os

import httpx


def main() -> None:
    token = os.environ["MAX_BOT_TOKEN"]
    secret = os.environ["MAX_WEBHOOK_SECRET"]
    base_url = os.environ["BOT_PUBLIC_BASE_URL"].rstrip("/")
    api_base = os.environ.get("MAX_API_BASE_URL", "https://platform-api2.max.ru")
    payload = {
        "url": f"{base_url}/webhooks/max",
        "update_types": ["bot_started", "message_created", "message_callback"],
        "secret": secret,
    }
    response = httpx.post(
        f"{api_base}/subscriptions",
        headers={"Authorization": token, "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    main()

