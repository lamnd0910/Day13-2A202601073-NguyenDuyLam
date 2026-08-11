from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import logging_config
from app.main import agent, app
from app.pii import hash_user_id

ENRICHMENT_FIELDS = {"user_id_hash", "session_id", "feature", "model", "env"}

CHAT_BODY = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "Explain observability",
}


@pytest.fixture
def log_path(monkeypatch, tmp_path: Path) -> Path:
    path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", path)
    return path


def read_events(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def api_events(log_path: Path) -> list[dict]:
    return [event for event in read_events(log_path) if event.get("service") == "api"]


def test_api_events_carry_full_request_context(log_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=CHAT_BODY)

    events = api_events(log_path)
    assert {event["event"] for event in events} >= {"request_received", "response_sent"}
    for event in events:
        assert ENRICHMENT_FIELDS.issubset(event.keys()), event["event"]
        assert event["correlation_id"] == response.headers["x-request-id"]


def test_context_values_match_request(log_path: Path) -> None:
    with TestClient(app) as client:
        client.post("/chat", json=CHAT_BODY)

    event = next(e for e in api_events(log_path) if e["event"] == "response_sent")
    assert event["user_id_hash"] == hash_user_id(CHAT_BODY["user_id"])
    assert event["session_id"] == CHAT_BODY["session_id"]
    assert event["feature"] == CHAT_BODY["feature"]
    assert event["model"] == agent.model


def test_raw_user_id_never_reaches_logs(log_path: Path) -> None:
    with TestClient(app) as client:
        client.post("/chat", json=CHAT_BODY)

    assert CHAT_BODY["user_id"] not in log_path.read_text(encoding="utf-8")


def test_correlation_id_is_never_missing_for_api_events(log_path: Path) -> None:
    with TestClient(app) as client:
        client.post("/chat", json=CHAT_BODY)
        client.post("/chat", json=CHAT_BODY)

    events = api_events(log_path)
    assert all(event["correlation_id"] != "MISSING" for event in events)
    assert len({event["correlation_id"] for event in events}) == 2


def test_context_does_not_leak_between_requests(log_path: Path) -> None:
    with TestClient(app) as client:
        client.post("/chat", json=CHAT_BODY)
        client.post("/chat", json={**CHAT_BODY, "session_id": "session-02"})

    sessions = [
        event["session_id"]
        for event in api_events(log_path)
        if event["event"] == "response_sent"
    ]
    assert sessions == ["session-01", "session-02"]
