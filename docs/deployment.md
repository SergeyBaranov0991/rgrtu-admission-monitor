# Deployment

MVP target is a separate VPS with a public HTTPS route to the MAX webhook. The bot repository starts
the application and Caddy only; any host-level routing is server-specific infrastructure and is kept
outside this repository.

Current production VPS: `194.226.163.137`.
Current public MAX webhook base URL: `https://rgrtu.194.226.163.137.sslip.io`.

1. Copy `.env.example` to `.env` and fill secrets.
2. Point the domain to the VPS, or use the configured `sslip.io` DNS name.
3. Replace `rgrtu.194.226.163.137.sslip.io` in `Caddyfile` if a dedicated domain is assigned later.
4. Run `docker compose up -d --build`.
5. Check `https://rgrtu.194.226.163.137.sslip.io/health/ready`.
6. Register webhook with `python scripts/register_webhook.py`.

The app remains ready when RGRTU or MAX is temporarily unavailable.

## Existing VPS with another project

If the public HTTPS route belongs to another nginx/Caddy project, use:

```bash
docker compose -p rgrtu-max-bot -f docker-compose.bot.yml up -d --build
curl -fsS http://127.0.0.1:8030/health/ready
```

The bot then runs privately on `127.0.0.1:8030`. A public MAX webhook still requires a separate
domain routed by the existing reverse proxy or another VPS.
