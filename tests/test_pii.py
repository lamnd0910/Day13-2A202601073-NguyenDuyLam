from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    out = scrub_text("My CCCD is 012345678901.")
    assert "012345678901" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    out1 = scrub_text("My card: 4111 1111 1111 1111")
    out2 = scrub_text("My card: 4111-1111-1111-1111")
    assert "4111" not in out1
    assert "4111" not in out2
    assert "REDACTED_CREDIT_CARD" in out1
    assert "REDACTED_CREDIT_CARD" in out2


def test_no_pii_unchanged() -> None:
    text = "Hello, this is a normal string."
    assert scrub_text(text) == text


def test_recursive_scrub() -> None:
    from app.logging_config import recursive_scrub

    data = {
        "user": {
            "email": "student@vinuni.edu.vn",
            "phones": ["0901234567", "090 123 4567"]
        },
        "message": "Hello, here is my card 4111 1111 1111 1111"
    }
    scrubbed = recursive_scrub(data)
    
    assert "student@" not in str(scrubbed)
    assert "0901234567" not in str(scrubbed)
    assert "4111" not in str(scrubbed)
    assert "REDACTED_EMAIL" in scrubbed["user"]["email"]
    assert "REDACTED_PHONE_VN" in scrubbed["user"]["phones"][0]
    assert "REDACTED_CREDIT_CARD" in scrubbed["message"]
