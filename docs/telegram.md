# Telegram Fork

Telegram is wired as an independent long-polling worker. It reuses the same command handler and
admission estimate code as the MAX bot, but does not need a public HTTPS webhook for testing.

## Local run

```bash
cp .env.tg.example .env.tg
# fill TELEGRAM_BOT_TOKEN
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
```

Use `/start` in Telegram. If `TELEGRAM_ALLOWED_CHAT_ID` is empty, the bot replies with the chat id
so access can be locked down after the first test.

Multiple family members can be allowed with the same variable:

```dotenv
TELEGRAM_ALLOWED_CHAT_ID=262214021,123456789,987654321
```

If access is already locked down, a new user still gets a rejection message with their own
`chat_id`; add it to the comma-separated list and restart the TG container.

For day-to-day changes, edit `config/telegram_allowed_chat_ids.txt` in the repository and push to
`main`. The deploy workflow syncs the file to the server and recreates the TG container.

## VPS side-by-side run

```bash
cd /opt/rgrtu-tg-bot
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml logs --tail=100 tg-bot
```

No host ports are published. This service does not touch nginx, Caddy, or the MAX bot compose
project.

On the current VPS, DNS resolves `api.telegram.org` to an address that times out. The compose file
pins only the TG container to `149.154.167.220` via `extra_hosts`; remove that line if normal DNS
works in another environment.

## Telegram API methods used

- `deleteWebhook` before polling, optional.
- `getUpdates` for long polling.
- `sendMessage` for replies.
