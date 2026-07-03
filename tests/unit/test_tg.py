from app.tg.client import extract_message, normalize_command
from app.config import Settings
from app.bot.keyboards import STATUS_BUTTON_TEXT
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


def test_settings_parses_multiple_allowed_chat_ids() -> None:
    settings = Settings(
        telegram_allowed_chat_id="262214021, 111;222\n333",
        telegram_allowed_chat_ids_file="missing-test-file.txt",
    )

    assert settings.telegram_allowed_chat_ids == {"262214021", "111", "222", "333"}


def test_settings_reads_allowed_chat_ids_file(tmp_path) -> None:
    config_file = tmp_path / "ids.txt"
    config_file.write_text("# comment\n262214021\n123456789 # family\n", encoding="utf-8")
    settings = Settings(telegram_allowed_chat_ids_file=str(config_file))

    assert settings.telegram_allowed_chat_ids == {"262214021", "123456789"}


async def test_send_message_adds_status_keyboard(monkeypatch) -> None:
    settings = Settings(telegram_bot_token="token", telegram_allowed_chat_ids_file="missing.txt")
    client = TelegramClient(settings)
    calls: list[dict] = []

    async def fake_post(method: str, payload: dict) -> dict:
        calls.append({"method": method, "payload": payload})
        return {}

    monkeypatch.setattr(client, "_post", fake_post)

    await client.send_message("123", "hello")

    assert calls[0]["method"] == "sendMessage"
    assert calls[0]["payload"]["reply_markup"]["keyboard"][0] == [{"text": STATUS_BUTTON_TEXT}]
