# Telegram Client Proxy

The production VPS runs a private Telegram MTProto proxy for regular Telegram clients.

Public endpoint:

```text
194.226.163.137:443
```

Public port `443` is shared by HAProxy:

- TLS traffic goes to Caddy/MAX on `127.0.0.1:9443`;
- non-TLS MTProto traffic goes to `rgrtu-mtproxy` on `127.0.0.1:9444`.

The proxy secret is intentionally not stored in the repository.

## Runtime

```bash
systemctl status haproxy
docker container ls | grep rgrtu-mtproxy
docker logs --tail=80 rgrtu-mtproxy
```

## Restart

```bash
systemctl restart haproxy
docker restart rgrtu-mtproxy
```

## Client Setup

Use Telegram's built-in MTProto proxy settings or a `t.me/proxy` link with:

```text
server=194.226.163.137
port=443
secret=<private MTProto secret>
```
