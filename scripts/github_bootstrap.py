from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OWNER = "SergeyBaranov0991"
REPO = "rgrtu-admission-monitor"
REPO_FULL_NAME = f"{OWNER}/{REPO}"


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    user = request_json("GET", "/user", token)
    login = user["login"]
    print(f"Authenticated as {login}")
    if login != OWNER:
        print(f"Warning: token owner is {login}, requested owner is {OWNER}", file=sys.stderr)

    repo = ensure_repo(token)
    print(f"Repository: {repo['html_url']}")

    ensure_git_repo(token, repo["clone_url"])
    configure_actions_secrets(token)
    print("Bootstrap complete")


def ensure_repo(token: str) -> dict[str, Any]:
    payload = {
        "name": REPO,
        "description": "RGRTU admission monitor bot for Telegram/MAX",
        "private": True,
        "auto_init": False,
        "has_issues": True,
    }
    try:
        return request_json("POST", "/user/repos", token, payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 422 and "name already exists" in body.lower():
            return request_json("GET", f"/repos/{REPO_FULL_NAME}", token)
        if exc.code == 403:
            try:
                return request_json("GET", f"/repos/{REPO_FULL_NAME}", token)
            except urllib.error.HTTPError:
                pass
        raise RuntimeError(f"create repo failed: {exc.code} {body}") from exc


def ensure_git_repo(token: str, clone_url: str) -> None:
    run(["git", "init"])
    run(["git", "config", "user.name", "Codex Deploy Bot"])
    run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"])
    if sys.platform == "win32":
        run(["git", "config", "http.sslBackend", "schannel"])
    run(["git", "branch", "-M", "main"])

    remotes = subprocess.run(
        ["git", "remote"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.splitlines()
    if "origin" in remotes:
        run(["git", "remote", "set-url", "origin", clone_url])
    else:
        run(["git", "remote", "add", "origin", clone_url])

    run(["git", "add", "-A"])
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    if status:
        run(["git", "commit", "-m", "Initial RGRTU bot implementation"])
    else:
        print("No local changes to commit")

    with tempfile.TemporaryDirectory() as tmp:
        askpass = Path(tmp) / "git-askpass.ps1"
        askpass.write_text(
            "param([string]$Prompt)\n"
            "if ($Prompt -match 'Username') { 'x-access-token' } else { $env:GITHUB_TOKEN }\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = token
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_TERMINAL_PROMPT"] = "0"
        run(["git", "push", "-u", "origin", "main"], env=env)


def configure_actions_secrets(token: str) -> None:
    try:
        public_key = request_json("GET", f"/repos/{REPO_FULL_NAME}/actions/secrets/public-key", token)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            print("Skipping Actions secrets: token has no repository secrets permission")
            print("Configure deploy secrets manually")
            return
        raise
    secrets = deploy_secrets_from_env()
    if not secrets:
        print("No deploy secret environment variables found; skipping Actions secrets")
        return
    for name, value in secrets.items():
        encrypted = encrypt_secret(public_key["key"], value)
        request_json(
            "PUT",
            f"/repos/{REPO_FULL_NAME}/actions/secrets/{name}",
            token,
            {"encrypted_value": encrypted, "key_id": public_key["key_id"]},
        )
        print(f"Secret configured: {name}")


def deploy_secrets_from_env() -> dict[str, str]:
    secrets = {}
    ssh_key_path = os.environ.get("DEPLOY_SSH_KEY_PATH", "").strip()
    if ssh_key_path:
        secrets["DEPLOY_SSH_KEY"] = Path(ssh_key_path).read_text(encoding="utf-8")
    for name in ("DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_PATH", "DEPLOY_MAX_PATH"):
        value = os.environ.get(name, "").strip()
        if value:
            secrets[name] = value
    return secrets


def encrypt_secret(public_key_b64: str, value: str) -> str:
    try:
        from nacl import public
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynacl"])
        from nacl import public

    public_key = public.PublicKey(base64.b64decode(public_key_b64))
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def request_json(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rgrtu-admission-monitor-bootstrap",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
    if not content:
        return {}
    return json.loads(content.decode("utf-8"))


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    print(f"+ {printable}")
    subprocess.run(command, check=True, env=env)


if __name__ == "__main__":
    main()
