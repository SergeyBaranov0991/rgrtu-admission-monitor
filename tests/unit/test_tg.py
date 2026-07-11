from app.bot.commands import CommandContext
from app.config import Settings
from app.bot.keyboards import RELATIVE_STATUS_BUTTON_TEXT
from app.tg import runner
from app.tg.client import extract_message, normalize_command
from app.tg.client import TelegramClient


def test_extract_message() -> None:
    update = {"update_id": 7, "message": {"chat": {"id": 123}, "text": "/status"}}

    message = extract_message(update)

    assert message is not None
    assert message.update_id == 7
    assert message.chat_id == "123"
    assert message.text == "/status"


def test_normalize_command_removes_bot_username() -> None:
    assert normalize_command("/status@RgrtuBot") == "/status"
    assert normalize_command("/program@RgrtuBot 09.03.02") == "/program 09.03.02"


async def test_send_message_adds_status_keyboard(monkeypatch) -> None:
    settings = Settings(telegram_bot_token="token")
    client = TelegramClient(settings)
    calls: list[dict] = []

    async def fake_post(method: str, payload: dict) -> dict:
        calls.append({"method": method, "payload": payload})
        return {}

    monkeypatch.setattr(client, "_post", fake_post)

    await client.send_message("123", "hello")

    assert calls[0]["method"] == "sendMessage"
    assert calls[0]["payload"]["reply_markup"]["keyboard"][0] == [{"text": RELATIVE_STATUS_BUTTON_TEXT}]


async def test_runner_accepts_any_chat_id(monkeypatch) -> None:
    contexts: list[CommandContext] = []
    sent: list[tuple[str, str]] = []

    class FakeClient:
        async def send_message(self, chat_id: str, text: str) -> None:
            sent.append((chat_id, text))

    async def fake_handle_command(context: CommandContext) -> str:
        contexts.append(context)
        return "ok"

    monkeypatch.setattr(runner, "get_settings", lambda: Settings())
    monkeypatch.setattr(runner, "handle_command", fake_handle_command)

    await runner._handle_message(FakeClient(), "999", "/start")

    assert contexts[0].user_id == "tg:999"
    assert contexts[0].text == "/start"
    assert sent == [("999", "ok")]
