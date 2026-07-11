# Deployment

Production uses one VPS with two independent compose projects:

- `rgrtu-max-bot` from `docker-compose.yml` for the MAX webhook app and Caddy.
- `rgrtu-tg-bot` from `docker-compose.tg.yml` for Telegram long polling.

The MAX compose file binds Caddy to `127.0.0.1:${CADDY_HTTPS_HOST_PORT:-9443}`. Any public
host-level routing in front of that port is server-specific infrastructure and is kept outside this
repository.

Production hostnames, IP addresses, SSH users, and filesystem paths are deployment-specific and are
not stored in the public repository. Keep local operational notes in `docs/local/`; that directory
is ignored by git.

1. Copy `.env.example` to `.env` and fill MAX secrets.
2. Set `MAX_PUBLIC_HOST` in `.env` to the public hostname routed to this bot.
3. Point the domain to the VPS or configure the host-level reverse proxy.
4. Run `docker compose -p rgrtu-max-bot -f docker-compose.yml up -d --build --remove-orphans`.
5. Check `https://<max-public-host>/health/ready`.
6. Register webhook with `python scripts/register_webhook.py`.

The app remains ready when RGRTU or MAX is temporarily unavailable.

## GitHub Actions Deploy

Pushes to `main` run:

```bash
python -m ruff check .
pytest -q
```

Configure these GitHub repository secrets for deployment:

```text
DEPLOY_SSH_KEY=<private SSH key with access to the server>
DEPLOY_HOST=<deployment host>
DEPLOY_USER=<ssh user>
DEPLOY_PATH=<Telegram bot path on the host>
DEPLOY_MAX_PATH=<MAX bot path on the host>
```

If all deploy secrets are configured, the workflow syncs the checkout to the configured Telegram and
MAX paths and recreates both compose projects. Local `.env`, `.env.tg`, `.env.local`,
`.env.*.local`, `.venv`, `Caddyfile.local`, `data`, `docs/local`, and `output` paths on the server
are not overwritten by rsync.

If any deploy secret is absent, the workflow keeps CI green and skips deployment with a notice.

## Existing VPS with another project

If the public HTTPS route belongs to another nginx/Caddy project, use:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.bot.yml up -d --build
curl -fsS http://127.0.0.1:8030/health/ready
```

The bot then runs privately on `127.0.0.1:8030`. A public MAX webhook still requires a separate
domain routed by the existing reverse proxy or another VPS.
