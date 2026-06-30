from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.bot.commands import CommandContext, handle_command
from app.bot.max_client import MaxClient
from app.config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/max")
async def max_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_max_bot_api_secret: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    expected = settings.max_webhook_secret.get_secret_value() if settings.max_webhook_secret else None
    if expected and x_max_bot_api_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook secret")

    payload = await request.json()
    background_tasks.add_task(process_update, payload)
    return {"ok": True}


async def process_update(payload: dict) -> None:
    settings = get_settings()
    text, user_id = extract_text_and_user(payload)
    if not text:
        return
    reply = await handle_command(CommandContext(user_id=user_id, text=text, settings=settings))
    if user_id and settings.max_bot_token:
        await MaxClient(settings).send_message(user_id, reply)


def extract_text_and_user(payload: dict) -> tuple[str | None, str | None]:
    update_type = payload.get("update_type") or payload.get("update", {}).get("update_type")
    if update_type == "bot_started":
        user = payload.get("user") or payload.get("update", {}).get("user") or {}
        user_id = str(user.get("user_id") or user.get("id") or payload.get("user_id") or "") or None
        return "/start", user_id

    message = payload.get("message") or payload.get("update", {}).get("message") or {}
    body = message.get("body") if isinstance(message.get("body"), dict) else message
    text = body.get("text") or payload.get("text")

    user = message.get("sender") or message.get("user") or payload.get("user") or {}
    user_id = str(user.get("user_id") or user.get("id") or payload.get("user_id") or "") or None
    return text, user_id
