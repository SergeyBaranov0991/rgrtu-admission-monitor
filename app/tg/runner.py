from __future__ import annotations

import asyncio
import logging

from app.bot.commands import CommandContext, handle_command
from app.config import get_settings
from app.observability.logging import configure_logging
from app.tg.client import TelegramClient, extract_message, normalize_command

logger = logging.getLogger(__name__)


async def run_polling() -> None:
    configure_logging()
    settings = get_settings()
    client = TelegramClient(settings)
    bot = await client.get_me()
    logger.info("telegram_polling_start bot=%s", bot.get("username"))

    if settings.telegram_delete_webhook_on_start:
        await client.delete_webhook(
            drop_pending_updates=settings.telegram_drop_pending_updates_on_start
        )

    offset: int | None = None
    while True:
        try:
            updates = await client.get_updates(offset=offset)
            for update in updates:
                update_id = int(update["update_id"])
                offset = update_id + 1
                message = extract_message(update)
                if message is None:
                    continue
                await _handle_message(client, message.chat_id, message.text)
        except Exception:
            logger.exception("telegram_polling_error")
            await asyncio.sleep(5)
        else:
            if not updates:
                await asyncio.sleep(settings.telegram_poll_interval_seconds)


async def _handle_message(client: TelegramClient, chat_id: str, text: str) -> None:
    settings = get_settings()
    command = normalize_command(text)
    reply = await handle_command(CommandContext(user_id=f"tg:{chat_id}", text=command, settings=settings))
    await client.send_message(chat_id, reply)


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
