# Runbook

## Containers

```bash
cd /opt/rgrtu-max-bot
docker compose -p rgrtu-max-bot -f docker-compose.yml ps
docker compose -p rgrtu-max-bot -f docker-compose.yml logs --tail=200 bot

cd /opt/rgrtu-tg-bot
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
curl -fsS https://rgrtu.194.226.163.137.sslip.io/health/ready
curl -fsS https://rgrtu.194.226.163.137.sslip.io/health/live
```

## Deploy

The normal deploy path is a push to `main`; GitHub Actions runs lint/tests and recreates both
compose projects on the VPS.

Manual MAX redeploy:

```bash
cd /opt/rgrtu-max-bot
docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans
```

Manual Telegram redeploy:

```bash
cd /opt/rgrtu-tg-bot
docker compose -p rgrtu-tg-bot -f docker-compose.tg.yml up -d --build --force-recreate
```

## Backup

```bash
bash scripts/backup_db.sh
```
