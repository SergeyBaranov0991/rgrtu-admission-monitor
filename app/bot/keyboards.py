from __future__ import annotations


def main_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {"type": "callback", "text": "Проверить сейчас", "payload": "/check"},
                    {"type": "callback", "text": "Текущий статус", "payload": "/status"},
                ],
                [
                    {"type": "callback", "text": "История", "payload": "/history"},
                    {"type": "callback", "text": "Направления", "payload": "/programs"},
                ],
            ]
        },
    }

