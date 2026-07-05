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
saved score/code/category/onboarding settings under `tg:<chat_id>`.

The reply keyboard includes both status modes:

- `Актуальный статус вне приоритетов` uses the published list order/scores.
- `Актуальный относительный статус` filters applicants that already pass by a higher priority within
  the selected category scope.

Use `/setup` to configure a chat. The first answer is either the RGRTU service entrant code or a
score. A long numeric code completes setup immediately: the bot derives specialties and priorities
from RGRTU rows with that code. A 3-digit score switches to score mode and asks for manual specialty
priorities in the form `01.03.02;1`; those manual priorities are used only in score mode.

Status replies are compact by default. Send `/debug` to toggle detailed output for the current chat;
send `/debug on` or `/debug off` to set it explicitly. Detailed output includes source status,
scored-row counts, calculation notes, priority-filter details, and forecast fields.

Changes pushed to `main` run lint/tests and recreate the TG container through the deploy workflow.

## VPS side-by-side run

```bash
cd /opt/rgrtu-tg-bot
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml logs --tail=100 tg-bot
```

No host ports are published. This service does not touch nginx, Caddy, or the MAX bot compose
project.

## Telegram API methods used

- `deleteWebhook` before polling, optional.
- `getUpdates` for long polling.
- `sendMessage` for replies.
