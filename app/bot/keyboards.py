from __future__ import annotations


STATUS_COMMAND = "/status"
STATUS_BUTTON_TEXT = "Статус без приоритетов"
RELATIVE_STATUS_COMMAND = "/relative_status"
RELATIVE_STATUS_BUTTON_TEXT = "Статус с приоритетами"
SEARCH_BY_SCORE_BUTTON_TEXT = "Искать по баллу"
SEARCH_BY_CODE_BUTTON_TEXT = "Искать по коду"
SETUP_BUTTON_TEXT = "Настроить профиль"
SETTINGS_BUTTON_TEXT = "Показать настройки"
MY_PROGRAMS_BUTTON_TEXT = "Мои направления"
ALL_PROGRAMS_BUTTON_TEXT = "Все направления"
GENERAL_ONLY_BUTTON_TEXT = "Общий конкурс"
ALL_CATEGORIES_BUTTON_TEXT = "Все категории"
STATUS_ALIASES = {
    STATUS_COMMAND,
    "/check",
    "актуальный статус",
    "актуальный статус вне приоритетов",
    STATUS_BUTTON_TEXT.casefold(),
    "статус",
    "статус без приоритетов",
    "текущий статус",
    "проверить статус",
}
RELATIVE_STATUS_ALIASES = {
    RELATIVE_STATUS_COMMAND,
    "/relative",
    RELATIVE_STATUS_BUTTON_TEXT.casefold(),
    "актуальный относительный статус",
    "относительный статус",
    "статус с приоритетами",
    "статус с учетом приоритетов",
}
SEARCH_BY_SCORE_ALIASES = {SEARCH_BY_SCORE_BUTTON_TEXT.casefold(), "/profile score", "/score_mode"}
SEARCH_BY_CODE_ALIASES = {SEARCH_BY_CODE_BUTTON_TEXT.casefold(), "/profile code", "/code_mode"}
SETUP_ALIASES = {SETUP_BUTTON_TEXT.casefold(), "/setup", "/onboarding"}
SETTINGS_ALIASES = {SETTINGS_BUTTON_TEXT.casefold(), "/settings"}
MY_PROGRAMS_ALIASES = {MY_PROGRAMS_BUTTON_TEXT.casefold(), "/my_programs", "/programs mine"}
ALL_PROGRAMS_ALIASES = {ALL_PROGRAMS_BUTTON_TEXT.casefold(), "/all_programs", "/programs all"}
GENERAL_ONLY_ALIASES = {
    GENERAL_ONLY_BUTTON_TEXT.casefold(),
    "только общий конкурс",
    "/scope general",
    "/general",
}
ALL_CATEGORIES_ALIASES = {ALL_CATEGORIES_BUTTON_TEXT.casefold(), "/scope all", "/all_categories"}


def is_status_request(text: str) -> bool:
    return text.strip().casefold() in STATUS_ALIASES


def is_relative_status_request(text: str) -> bool:
    return text.strip().casefold() in RELATIVE_STATUS_ALIASES


def is_search_by_score_request(text: str) -> bool:
    return text.strip().casefold() in SEARCH_BY_SCORE_ALIASES


def is_search_by_code_request(text: str) -> bool:
    return text.strip().casefold() in SEARCH_BY_CODE_ALIASES


def is_setup_request(text: str) -> bool:
    return text.strip().casefold() in SETUP_ALIASES


def is_settings_request(text: str) -> bool:
    return text.strip().casefold() in SETTINGS_ALIASES


def is_my_programs_request(text: str) -> bool:
    return text.strip().casefold() in MY_PROGRAMS_ALIASES


def is_all_programs_request(text: str) -> bool:
    return text.strip().casefold() in ALL_PROGRAMS_ALIASES


def is_general_only_request(text: str) -> bool:
    return text.strip().casefold() in GENERAL_ONLY_ALIASES


def is_all_categories_request(text: str) -> bool:
    return text.strip().casefold() in ALL_CATEGORIES_ALIASES


def max_status_keyboard() -> dict:
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "message", "text": RELATIVE_STATUS_BUTTON_TEXT}],
                [{"type": "message", "text": STATUS_BUTTON_TEXT}],
                [
                    {"type": "message", "text": SETUP_BUTTON_TEXT},
                    {"type": "message", "text": SETTINGS_BUTTON_TEXT},
                ],
                [
                    {"type": "message", "text": MY_PROGRAMS_BUTTON_TEXT},
                    {"type": "message", "text": ALL_PROGRAMS_BUTTON_TEXT},
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
            [{"text": RELATIVE_STATUS_BUTTON_TEXT}],
            [{"text": STATUS_BUTTON_TEXT}],
            [{"text": SETUP_BUTTON_TEXT}, {"text": SETTINGS_BUTTON_TEXT}],
            [{"text": MY_PROGRAMS_BUTTON_TEXT}, {"text": ALL_PROGRAMS_BUTTON_TEXT}],
            [{"text": GENERAL_ONLY_BUTTON_TEXT}, {"text": ALL_CATEGORIES_BUTTON_TEXT}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Статус, профиль или режим",
    }
