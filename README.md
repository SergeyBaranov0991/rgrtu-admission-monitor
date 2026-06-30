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
- admission rank interval and zone estimation;
- fixture-backed CLI check;
- RGRTU Livewire subject discovery;
- Docker Compose and operational docs.

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
pytest
python -m app.cli check --score 195
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

GitHub Actions deployment needs these repository secrets:

```text
DEPLOY_HOST=92.51.39.164
DEPLOY_USER=root
DEPLOY_PATH=/opt/rgrtu-tg-bot
DEPLOY_SSH_KEY=<private SSH key with access to the server>
```

## Side-by-side VPS deployment

Use `docker-compose.bot.yml` when the VPS already has an nginx/Caddy project on ports 80/443:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.bot.yml up -d --build
curl -fsS http://127.0.0.1:8030/health/ready
```

This binds only `127.0.0.1:8030` on the host and does not touch the existing reverse proxy.

## Important

The current CLI calculation uses the fixture in `tests/fixtures/rgrtu/competition_list_full.json`.
The exact RGRTU row-fetching request still needs Network capture from the Livewire UI before live
snapshots are enabled.
