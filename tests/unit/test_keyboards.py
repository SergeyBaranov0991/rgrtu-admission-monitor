from app.bot.keyboards import (
    STATUS_BUTTON_TEXT,
    is_status_request,
    max_status_keyboard,
    telegram_status_reply_markup,
)


def test_status_button_text_is_status_request() -> None:
    assert is_status_request(STATUS_BUTTON_TEXT)
    assert is_status_request("/status")
    assert is_status_request("/check")


def test_max_keyboard_has_only_status_button() -> None:
    keyboard = max_status_keyboard()

    assert keyboard == {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "message", "text": STATUS_BUTTON_TEXT}],
            ]
        },
    }


def test_telegram_keyboard_has_only_status_button() -> None:
    markup = telegram_status_reply_markup()

    assert markup["keyboard"] == [[{"text": STATUS_BUTTON_TEXT}]]
    assert markup["resize_keyboard"] is True
