# Runbook

## Containers

```bash
docker compose ps
docker compose logs --tail=200 bot
```

## Local check

```bash
python -m app.cli check --score 195
```

## Discovery

```bash
python -m app.cli discover
```

## Health

```bash
curl -fsS https://rgrtu.194.226.163.137.sslip.io/health/ready
```

## Backup

```bash
bash scripts/backup_db.sh
```
