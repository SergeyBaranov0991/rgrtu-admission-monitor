# RGRTU Admission Monitor

MAX bot for monitoring RGRTU admission competition lists.

## Bot links

- MAX: <https://max.ru/se13437557_bot?start=rgrtu>
- MAX profile: <https://max.ru/se13437557_bot>
- Telegram: <https://t.me/monitoring_RGRTU_TG_bot>

Current implementation is the first MVP slice:

- FastAPI health endpoints and MAX webhook entrypoint;
- independent Telegram long-polling worker for faster testing;
- command handling skeleton;
- per-chat search profile: score or RGRTU service entrant code;
- category scope switch: only general competition or all categories;
- admission rank interval and zone estimation;
- live RGRTU public-list check through the official competition-list page payload;
- RGRTU Livewire subject discovery;
- Docker Compose and operational docs.

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
python -m ruff check .
pytest
python -m app.cli check --score 195
python -m app.cli check --score 195 --insecure
python -m app.cli check --score 195 --fixture tests/fixtures/rgrtu/competition_list_full.json
python -m app.cli discover
uvicorn app.main:app --reload
```

## Telegram test bot

```bash
cp .env.tg.example .env.tg
# fill TELEGRAM_BOT_TOKEN
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build
```

Allow several Telegram chats by comma-separating ids:

```dotenv
TELEGRAM_ALLOWED_CHAT_ID=262214021,123456789
```

For normal edits, prefer [config/telegram_allowed_chat_ids.txt](config/telegram_allowed_chat_ids.txt):

```text
262214021
123456789
```

Changes pushed to `main` are deployed by GitHub Actions.

## Bot Controls

Both MAX and Telegram show the same reply buttons:

- `Актуальный статус` - refresh current estimates.
- `Искать по баллу` - switch to score profile and wait for a numeric score.
- `Искать по коду` - switch to RGRTU service-code profile and wait for a numeric entrant code.
- `Только общий конкурс` - show only the main budget general-competition category.
- `Все категории` - show quotas, target admission, general competition, and contract categories for
  the tracked full-time profile.

Text commands are also supported:

```text
/score 195
/achievements 5
/code 1158236
/scope general
/scope all
/settings
```

GitHub Actions deployment uses the production host/path from
[.github/workflows/deploy.yml](.github/workflows/deploy.yml). It needs this repository secret:

```text
DEPLOY_SSH_KEY=<private SSH key with access to the server>
```

If `DEPLOY_SSH_KEY` is absent, the workflow keeps tests green and skips deploy with a notice.

## Side-by-side VPS deployment

Production VPS: `194.226.163.137`.
Production MAX webhook base URL: `https://rgrtu.194.226.163.137.sslip.io`.

Use `docker-compose.yml` on the dedicated bot VPS. It starts the MAX webhook app and Caddy. The
compose file binds Caddy to `127.0.0.1:${CADDY_HTTPS_HOST_PORT:-9443}` so public routing can stay in
server-specific infrastructure outside this repository:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build
curl -fsS https://rgrtu.194.226.163.137.sslip.io/health/ready
```

Use `docker-compose.bot.yml` only when the VPS already has an nginx/Caddy project on ports 80/443:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.bot.yml up -d --build
curl -fsS http://127.0.0.1:8030/health/ready
```

This binds only `127.0.0.1:8030` on the host and does not touch the existing reverse proxy.

## RGRTU Data Sources

The bot reads current public data from:

- public competition overview page: <https://postupai.rsreu.ru/guest/competition-lists/20>
- Livewire component embedded in that page: `competition-lists-common`
- direct competition pages selected from `competitions[].id`, for example:
  <https://postupai.rsreu.ru/guest/competition-lists/20/1863247416534381847>

`RGRTU_CAMPAIGN_ID` controls the campaign id. The current value `20` is the RGRTU
`Бакалавриат и специалитет 2026/2027` campaign. The overview payload contains the official
`submitted` counter used for `Подано заявлений`, while entrant rows are sanitized before internal
use. Local Windows checks may need `--insecure` if TLS verification is intercepted; Docker trusts
the bundled Russian CA chain.
