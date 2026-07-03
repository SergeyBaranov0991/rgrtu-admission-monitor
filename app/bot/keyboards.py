from __future__ import annotations


STATUS_COMMAND = "/status"
STATUS_BUTTON_TEXT = "Актуальный статус"
SEARCH_BY_SCORE_BUTTON_TEXT = "Искать по баллу"
SEARCH_BY_CODE_BUTTON_TEXT = "Искать по коду"
GENERAL_ONLY_BUTTON_TEXT = "Только общий конкурс"
ALL_CATEGORIES_BUTTON_TEXT = "Все категории"
STATUS_ALIASES = {
    STATUS_COMMAND,
    "/check",
    STATUS_BUTTON_TEXT.casefold(),
    "статус",
    "текущий статус",
    "проверить статус",
}
SEARCH_BY_SCORE_ALIASES = {SEARCH_BY_SCORE_BUTTON_TEXT.casefold(), "/profile score", "/score_mode"}
SEARCH_BY_CODE_ALIASES = {SEARCH_BY_CODE_BUTTON_TEXT.casefold(), "/profile code", "/code_mode"}
GENERAL_ONLY_ALIASES = {GENERAL_ONLY_BUTTON_TEXT.casefold(), "/scope general", "/general"}
ALL_CATEGORIES_ALIASES = {ALL_CATEGORIES_BUTTON_TEXT.casefold(), "/scope all", "/all_categories"}


def is_status_request(text: str) -> bool:
    return text.strip().casefold() in STATUS_ALIASES


def is_search_by_score_request(text: str) -> bool:
    return text.strip().casefold() in SEARCH_BY_SCORE_ALIASES


def is_search_by_code_request(text: str) -> bool:
    return text.strip().casefold() in SEARCH_BY_CODE_ALIASES


def is_general_only_request(text: str) -> bool:
    return text.strip().casefold() in GENERAL_ONLY_ALIASES


def is_all_categories_request(text: str) -> bool:
    return text.strip().casefold() in ALL_CATEGORIES_ALIASES


def max_status_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "message", "text": STATUS_BUTTON_TEXT}],
                [
                    {"type": "message", "text": SEARCH_BY_SCORE_BUTTON_TEXT},
                    {"type": "message", "text": SEARCH_BY_CODE_BUTTON_TEXT},
                ],
                [
                    {"type": "message", "text": GENERAL_ONLY_BUTTON_TEXT},
                    {"type": "message", "text": ALL_CATEGORIES_BUTTON_TEXT},
                ],
            ]
        },
    }


def telegram_status_reply_markup() -> dict:
    return {
        "keyboard": [
            [{"text": STATUS_BUTTON_TEXT}],
            [{"text": SEARCH_BY_SCORE_BUTTON_TEXT}, {"text": SEARCH_BY_CODE_BUTTON_TEXT}],
            [{"text": GENERAL_ONLY_BUTTON_TEXT}, {"text": ALL_CATEGORIES_BUTTON_TEXT}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Статус, балл, код или режим",
    }
