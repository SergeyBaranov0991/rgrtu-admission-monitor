from app.api.max_webhook import extract_text_and_user


def test_extract_text_and_user_from_message_payload() -> None:
    payload = {"message": {"body": {"text": "/status"}, "sender": {"user_id": 123}}}

    text, user_id = extract_text_and_user(payload)

    assert text == "/status"
    assert user_id == "123"

