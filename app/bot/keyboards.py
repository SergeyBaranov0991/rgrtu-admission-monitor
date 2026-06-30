from __future__ import annotations


STATUS_COMMAND = "/status"
STATUS_BUTTON_TEXT = "Актуальный статус"
STATUS_ALIASES = {
    STATUS_COMMAND,
    "/check",
    STATUS_BUTTON_TEXT.casefold(),
    "статус",
    "текущий статус",
    "проверить статус",
}


def is_status_request(text: str) -> bool:
    return text.strip().casefold() in STATUS_ALIASES


def max_status_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "message", "text": STATUS_BUTTON_TEXT}],
            ]
        },
    }


def telegram_status_reply_markup() -> dict:
    return {
        "keyboard": [[{"text": STATUS_BUTTON_TEXT}]],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Нажмите кнопку для обновления статуса",
    }
