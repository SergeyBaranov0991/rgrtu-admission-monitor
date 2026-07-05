# RGRTU Admission Monitor

MAX bot for monitoring RGRTU admission competition lists.

## Bot links

- MAX: <https://max.ru/se13437557_bot?start=rgrtu>
- MAX profile: <https://max.ru/se13437557_bot>
- Telegram: <https://t.me/monitoring_RGRTU_TG_bot>

Current implementation is the first MVP slice:

- FastAPI health endpoints and MAX webhook entrypoint;
- independent Telegram long-polling worker for faster testing;
- shared command handling for MAX and Telegram;
- per-chat settings stored in SQLite through `app.bot.user_settings`;
- per-chat search profile: score or RGRTU service entrant code;
- per-chat onboarding: code-based setup skips manual priorities, score-based setup asks for
  specialty priorities;
- category scope switch: only general competition or all categories;
- admission rank interval and zone estimation;
- relative admission estimate that filters applicants passing by higher priority in the selected
  category scope;
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
python -m app.cli check --score 195 --relative
python -m app.cli check --code 1158236 --relative
python -m app.cli check --code 1158236 --relative --debug
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

Telegram access is not restricted by chat id. Changes pushed to `main` are deployed by GitHub
Actions.

## Code Structure

- `app.bot.commands` routes user commands and button text.
- `app.bot.user_settings` loads and saves per-chat score/code/category/debug/onboarding settings.
- `app.bot.profile` parses and stores score-profile specialty priorities.
- `app.bot.messages` renders human-readable MAX/Telegram responses.
- `app.admission.estimator` computes rank, passing-score, confidence, and forecast fields.
- `app.admission.relative` builds priority-aware competition lists for relative status.
- `app.rgrtu.livewire_adapter` fetches current public RGRTU competition-list payloads.

## Bot Controls

Both MAX and Telegram show the same reply buttons:

- `Актуальный статус вне приоритетов` - refresh estimates by the published list order/scores.
- `Актуальный относительный статус` - refresh estimates after filtering applicants that pass by a
  higher priority within the selected category scope.
- `Искать по баллу` - switch to score profile and wait for a numeric score.
- `Искать по коду` - switch to RGRTU service-code profile and wait for a numeric entrant code.
- `Только общий конкурс` - show only the main budget general-competition category.
- `Все категории` - show quotas, target admission, general competition, and contract categories for
  the tracked full-time profile.

Text commands are also supported:

```text
/status
/relative
/setup
/score 195
/achievements 5
/code 1158236
/scope general
/scope all
/settings
/debug
```

Status responses are compact by default. `/debug` toggles detailed responses for the current chat;
when enabled, status output includes source status, scored-row counts, calculation notes,
priority-filter details, and forecast fields. The CLI uses the same split: add `--debug` to print
the detailed form.

`/setup` configures the current chat. The first answer is either the RGRTU service entrant code or a
score. If the answer is a long numeric code, the bot stores code search and derives specialties and
priorities from the RGRTU rows where that code appears. If the answer is a 3-digit score, the bot
asks for manual specialty priorities in the form `01.03.02;1`; this manual profile is used only for
score-based status filtering and ordering.

GitHub Actions deployment uses the production host/path from
[.github/workflows/deploy.yml](.github/workflows/deploy.yml). It needs this repository secret:

```text
DEPLOY_SSH_KEY=<private SSH key with access to the server>
```

If `DEPLOY_SSH_KEY` is absent, the workflow keeps tests green and skips deploy with a notice.
The CI gate runs `python -m ruff check .` and `pytest -q` before deploying.

## Side-by-side VPS deployment

Production VPS: `194.226.163.137`.
Production MAX webhook base URL: `https://rgrtu.194.226.163.137.sslip.io`.

Use `docker-compose.yml` on the dedicated bot VPS. It starts the MAX webhook app and Caddy. The
compose file binds Caddy to `127.0.0.1:${CADDY_HTTPS_HOST_PORT:-9443}` so public routing can stay in
server-specific infrastructure outside this repository:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans
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

Relative status uses the same loaded competitions as the current category scope. A row with priority
`2..5` is excluded from a lower-priority list only when the same application code is confidently
passing in a higher-priority list. Ties on the passing boundary are kept in the lower-priority list
unless the whole equal-score interval fits into the available places. The compact chat response only
shows the result; `/help` and `/debug` expose the calculation details.
