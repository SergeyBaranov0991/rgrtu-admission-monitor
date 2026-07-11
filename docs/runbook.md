# Runbook

## Containers

```bash
cd "${DEPLOY_MAX_PATH}"
docker compose -p rgrtu-max-bot -f docker-compose.yml ps
docker compose -p rgrtu-max-bot -f docker-compose.yml logs --tail=200 bot

cd "${DEPLOY_PATH}"
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml ps
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml logs --tail=200 tg-bot
```

## Checks

```bash
python -m ruff check .
pytest -q
python -m app.cli check --score 195
python -m app.cli check --score 195 --relative
python -m app.cli check --code 1158236 --relative
python -m app.cli check --code 1158236 --relative --debug
```

## Discovery

```bash
python -m app.cli discover
```

## Health

```bash
curl -fsS https://<max-public-host>/health/ready
curl -fsS https://<max-public-host>/health/live
```

## Deploy

The normal deploy path is a push to `main`; GitHub Actions runs lint/tests and recreates both
compose projects on the VPS.

Manual MAX redeploy:

```bash
cd "${DEPLOY_MAX_PATH}"
docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans
```

Manual Telegram redeploy:

```bash
cd "${DEPLOY_PATH}"
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build --force-recreate
```

## Backup

```bash
bash scripts/backup_db.sh
```
