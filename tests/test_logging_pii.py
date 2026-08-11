from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.logging_config import get_logger
from app.main import app


def test_api_pii_redaction(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "u-456",
                "session_id": "s-456",
                "feature": "test",
                "message": (
                    "My email is student@vinuni.edu.vn "
                    "and my card is 4111 1111 1111 1111"
                ),
            },
        )

    assert response.status_code == 200

    raw = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw
    assert "4111 1111 1111 1111" not in raw
    assert "REDACTED_EMAIL" in raw
    assert "REDACTED_CREDIT_CARD" in raw


def test_exception_message_is_scrubbed(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "exception.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    logger = get_logger()

    try:
        raise ValueError("Contact student@vinuni.edu.vn")
    except ValueError:
        logger.exception("operation_failed")

    raw = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw
    assert "REDACTED_EMAIL" in raw
