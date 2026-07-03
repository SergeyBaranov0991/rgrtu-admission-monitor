# Deployment

Production uses one VPS with two independent compose projects:

- `rgrtu-max-bot` from `docker-compose.yml` for the MAX webhook app and Caddy.
- `rgrtu-tg-bot` from `docker-compose.tg.yml` for Telegram long polling.

The MAX compose file binds Caddy to `127.0.0.1:${CADDY_HTTPS_HOST_PORT:-9443}`. Any public
host-level routing in front of that port is server-specific infrastructure and is kept outside this
repository.

Current production VPS: `194.226.163.137`.
Current public MAX webhook base URL: `https://rgrtu.194.226.163.137.sslip.io`.

1. Copy `.env.example` to `.env` and fill MAX secrets.
2. Point the domain to the VPS, or use the configured `sslip.io` DNS name.
3. Replace `rgrtu.194.226.163.137.sslip.io` in `Caddyfile` if a dedicated domain is assigned later.
4. Run `docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans`.
5. Check `https://rgrtu.194.226.163.137.sslip.io/health/ready`.
6. Register webhook with `python scripts/register_webhook.py`.

The app remains ready when RGRTU or MAX is temporarily unavailable.

## GitHub Actions Deploy

Pushes to `main` run:

```bash
python -m ruff check .
pytest -q
```

If the `DEPLOY_SSH_KEY` repository secret is configured, the workflow syncs the checkout to:

- `/opt/rgrtu-tg-bot`
- `/opt/rgrtu-max-bot`

Then it recreates both compose projects. Local `.env`, `.env.tg`, `.venv`, `data`, and `output`
directories on the server are not overwritten by rsync.

## Existing VPS with another project

If the public HTTPS route belongs to another nginx/Caddy project, use:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.bot.yml up -d --build
curl -fsS http://127.0.0.1:8030/health/ready
```

The bot then runs privately on `127.0.0.1:8030`. A public MAX webhook still requires a separate
domain routed by the existing reverse proxy or another VPS.
