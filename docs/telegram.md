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

The reply keyboard groups status, profile setup, specialty scope, and category scope:

- `Статус с приоритетами` filters applicants only when the same code already passes by a
  higher priority. Budget and paid lists are evaluated independently.
- `Статус без приоритетов` uses the published list order/scores.
- `Настроить профиль` starts onboarding for a score or RGRTU service entrant code.
- `Показать настройки` shows the saved chat profile.
- `Мои направления` sets manual specialty priorities for score search.
- `Все направления` clears manual priorities and checks all full-time RGRTU specialties by score.
- `Общий конкурс` and `Все категории` switch category scope.

Use `/setup` to configure a chat. The first answer is either the RGRTU service entrant code or a
score. A long numeric code completes setup immediately; the first status request then loads all
full-time RGRTU competitions, finds up to 5 specialties where that code appears, and saves them to
the chat profile. A 3-digit score switches to score mode and checks all full-time RGRTU specialties
by default. Use `Мои направления` or `/my_programs` to narrow score search to manual specialty
priorities in the form `01.03.02;1`; use `Все направления` or `/all_programs` to return to all
full-time specialties.

For a code-based relative status, the filter is built from all full-time RGRTU competitions before
the reply is narrowed back to the saved chat profile. A lower-priority applicant remains in the
current list unless that applicant passes by a higher priority elsewhere. This mode does not filter
the list down to applicants with submitted enrollment consent. Consent/VPP/OVP fields are used only
when they are present in a concrete source list; if they are absent, debug reports "no data" rather
than treating the value as zero consents.

Status replies are compact by default and include a separate `Историка` line when prior-year data is
available. Send `/debug` to toggle detailed output for the current chat; send `/debug on` or
`/debug off` to set it explicitly. Detailed output includes source status, scored-row counts,
calculation notes, priority-filter details, consent/VPP/OVP data availability, and current plus
historical forecast fields.

Historical references are static constants in `app.admission.historical`: budget/general competition
uses the official RGRTU prior-year minimum and average scores page, while paid directions use the
official 2025 commercial enrollment orders.

Changes pushed to `main` run lint/tests and recreate the TG container through the deploy workflow.

## VPS side-by-side run

```bash
cd "${DEPLOY_PATH}"
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml logs --tail=100 tg-bot
```

No host ports are published. This service does not touch nginx, Caddy, or the MAX bot compose
project.

## Telegram API methods used

- `deleteWebhook` before polling, optional.
- `getUpdates` for long polling.
- `sendMessage` for replies.
