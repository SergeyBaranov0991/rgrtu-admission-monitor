from app.bot.keyboards import (
    ALL_CATEGORIES_BUTTON_TEXT,
    GENERAL_ONLY_BUTTON_TEXT,
    SEARCH_BY_CODE_BUTTON_TEXT,
    SEARCH_BY_SCORE_BUTTON_TEXT,
    RELATIVE_STATUS_BUTTON_TEXT,
    STATUS_BUTTON_TEXT,
    is_all_categories_request,
    is_general_only_request,
    is_relative_status_request,
    is_search_by_code_request,
    is_search_by_score_request,
    is_status_request,
    max_status_keyboard,
    telegram_status_reply_markup,
)


def test_status_button_text_is_status_request() -> None:
    assert is_status_request(STATUS_BUTTON_TEXT)
    assert is_status_request("Актуальный статус")
    assert is_status_request("/status")
    assert is_status_request("/check")
    assert is_relative_status_request(RELATIVE_STATUS_BUTTON_TEXT)
    assert is_relative_status_request("/relative")
    assert is_search_by_score_request(SEARCH_BY_SCORE_BUTTON_TEXT)
    assert is_search_by_code_request(SEARCH_BY_CODE_BUTTON_TEXT)
    assert is_general_only_request(GENERAL_ONLY_BUTTON_TEXT)
    assert is_all_categories_request(ALL_CATEGORIES_BUTTON_TEXT)


def test_max_keyboard_has_only_status_button() -> None:
    keyboard = max_status_keyboard()

    assert keyboard == {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "message", "text": STATUS_BUTTON_TEXT}],
                [{"type": "message", "text": RELATIVE_STATUS_BUTTON_TEXT}],
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


def test_telegram_keyboard_has_only_status_button() -> None:
    markup = telegram_status_reply_markup()

    assert markup["keyboard"] == [
        [{"text": STATUS_BUTTON_TEXT}],
        [{"text": RELATIVE_STATUS_BUTTON_TEXT}],
        [{"text": SEARCH_BY_SCORE_BUTTON_TEXT}, {"text": SEARCH_BY_CODE_BUTTON_TEXT}],
        [{"text": GENERAL_ONLY_BUTTON_TEXT}, {"text": ALL_CATEGORIES_BUTTON_TEXT}],
    ]
    assert markup["resize_keyboard"] is True
