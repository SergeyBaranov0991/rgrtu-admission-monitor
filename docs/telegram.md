# Telegram Fork

Telegram is wired as an independent long-polling worker. It reuses the same command handler and
admission estimate code as the MAX bot, but does not need a public HTTPS webhook for testing.

## Local run

```bash
cp .env.tg.example .env.tg
# fill TELEGRAM_BOT_TOKEN
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
```

Use `/start` in Telegram. Telegram access is not restricted by chat id; every chat gets its own
saved score/code/category settings under `tg:<chat_id>`.

Changes pushed to `main` run lint/tests and recreate the TG container through the deploy workflow.

## VPS side-by-side run

```bash
cd /opt/rgrtu-tg-bot
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml logs --tail=100 tg-bot
```

No host ports are published. This service does not touch nginx, Caddy, or the MAX bot compose
project.

On the current VPS, DNS resolves `api.telegram.org` to an address that times out. `docker-compose.tg.yml`
therefore pins only the TG container to `149.154.167.220` via `extra_hosts`. This is not a separate
Telegram client proxy; remove that line if normal DNS works in another environment.

## Telegram API methods used

- `deleteWebhook` before polling, optional.
- `getUpdates` for long polling.
- `sendMessage` for replies.
