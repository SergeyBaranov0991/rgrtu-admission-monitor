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
- per-chat onboarding: code-based setup auto-discovers up to 5 specialties on the first status
  request, score-based setup checks all full-time specialties by default and can be narrowed manually;
- category scope switch: only general competition or all categories;
- admission rank interval and zone estimation;
- relative admission estimate that filters only applicants already passing by a higher priority;
- live RGRTU public-list check through the official competition-list page payload;
- separate historical passing-score reference from official RGRTU prior-year data and 2025 paid
  enrollment orders;
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
- `app.admission.historical` stores official prior-year budget and paid passing-score references.
- `app.admission.relative` builds priority-aware competition lists for relative status.
- `app.rgrtu.livewire_adapter` fetches current public RGRTU competition-list payloads.

## Bot Controls

Both MAX and Telegram show the same reply buttons:

- `Статус с приоритетами` - refresh estimates after filtering applicants that pass by a
  higher priority. Budget and paid lists are evaluated independently.
- `Статус без приоритетов` - refresh estimates by the published list order/scores.
- `Настроить профиль` - start onboarding for a score or RGRTU service entrant code.
- `Показать настройки` - show the current chat profile.
- `Мои направления` - set a manual specialty-priority list for score search.
- `Все направления` - clear the manual list and check all full-time RGRTU specialties by score.
- `Общий конкурс` - show only the main budget general-competition category.
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
/my_programs
/all_programs
```

Status responses are compact by default and include a separate `Историка` line with prior-year
passing-score and average-score references when data is available. `/debug` toggles detailed
responses for the current chat; when enabled, status output includes source status, scored-row
counts, calculation notes, priority-filter details, consent/VPP/OVP data availability, and current
plus historical forecast fields. The CLI uses the same split: add `--debug` to print the detailed
form.

`/setup` configures the current chat. The first answer is either the RGRTU service entrant code or a
score. If the answer is a long numeric code, the bot stores code search; the first status request
loads all full-time RGRTU competitions, finds up to 5 specialties where that code appears, stores the
specialty profile, and then filters status output by that profile. If the answer is a 3-digit score,
the bot stores score search and checks all full-time RGRTU specialties by default. Use
`Мои направления` or `/my_programs` to narrow score search to manual specialty priorities in the form
`01.03.02;1`; use `Все направления` or `/all_programs` to return to all full-time specialties.

GitHub Actions deployment does not store production hostnames, IP addresses, users, or filesystem
paths in the public repository. Configure these repository secrets in GitHub:

```text
DEPLOY_SSH_KEY=<private SSH key with access to the server>
DEPLOY_HOST=<deployment host>
DEPLOY_USER=<ssh user>
DEPLOY_PATH=<Telegram bot path on the host>
DEPLOY_MAX_PATH=<MAX bot path on the host>
```

If any deploy secret is absent, the workflow keeps tests green and skips deploy with a notice. The
CI gate runs `python -m ruff check .` and `pytest -q` before deploying.

## Side-by-side VPS deployment

Production-specific values are intentionally kept out of git. Keep local notes in
`docs/local/deployment.local.md`; this directory is ignored by git.

Use `docker-compose.yml` on the dedicated bot VPS. It starts the MAX webhook app and Caddy. The
compose file binds Caddy to `127.0.0.1:${CADDY_HTTPS_HOST_PORT:-9443}` so public routing can stay in
server-specific infrastructure outside this repository. Set `MAX_PUBLIC_HOST` in the local `.env`:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans
curl -fsS https://<max-public-host>/health/ready
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

Historical references are static constants sourced from official RGRTU pages:

- budget/general competition minimum and average scores for prior years:
  <https://rsreu.ru/abitur/bachelor/srednie-i-minimalnye-prokhodnye-bally>
- paid 2025 enrollment order №932-д:
  <https://rsreu.ru/component/docman/doc_download/20635-prikaz-932-d-ot-28-08-2025-kommertsiya-ochnoe>
- paid 2025 foreign-student enrollment order №933-д:
  <https://rsreu.ru/component/docman/doc_download/20634-prikaz-933-d-ot-28-08-2025-kommertsiya-ochnoe>

`RGRTU_CAMPAIGN_ID` controls the campaign id. The current value `20` is the RGRTU
`Бакалавриат и специалитет 2026/2027` campaign. The overview payload contains the official
`submitted` counter used for `Подано заявлений`, while entrant rows are sanitized before internal
use. Local Windows checks may need `--insecure` if TLS verification is intercepted; Docker trusts
the bundled Russian CA chain.

Relative status excludes a row from a lower-priority list only when the same application code is
confidently passing in another list with a higher priority. Applicants are not removed merely because
their priority in the current list is lower than the target applicant's priority. Ties on the passing
boundary are kept in the lower-priority list unless the whole equal-score interval fits into the
available places. Budget and paid competitions are filtered separately because they use separate
priority sequences. This mode is priority-aware but does not filter the list down to applicants with
submitted enrollment consent. Consent/VPP/OVP fields are treated as unavailable unless they are
present in a concrete source list; absence of those fields is not interpreted as zero consents.

For a code-based relative profile, the bot loads all full-time RGRTU competitions first, builds the
higher-priority filter from that full universe, and only then filters the chat response back to the
saved specialty profile and selected category scope. The target application is kept in each of its
own priority lists so lower-priority blocks show the conditional position if the target does not end
up admitted by a higher priority. Relative positions use the order of the filtered published list.

Chat status blocks are sorted by specialty priority and use a `Приоритет N:` prefix in the block
heading.
