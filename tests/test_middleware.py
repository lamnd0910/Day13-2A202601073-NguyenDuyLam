from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import logging_config
from app.main import app

CORRELATION_ID_RE = re.compile(r"^req-[0-9a-f]{8}$")

CHAT_BODY = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "Explain observability",
}


@pytest.fixture
def client(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    with TestClient(app) as test_client:
        yield test_client


def test_generates_correlation_id_when_header_missing(client: TestClient) -> None:
    response = client.post("/chat", json=CHAT_BODY)

    assert response.status_code == 200
    assert CORRELATION_ID_RE.fullmatch(response.headers["x-request-id"])


def test_reuses_valid_inbound_correlation_id(client: TestClient) -> None:
    response = client.post(
        "/chat", json=CHAT_BODY, headers={"x-request-id": "req-abcdef12"}
    )

    assert response.headers["x-request-id"] == "req-abcdef12"


@pytest.mark.parametrize(
    "bad_id",
    ["not-a-request-id", "req-XYZ", "req-abcdef123", "req-abcdef1", "", "req-"],
)
def test_rejects_malformed_inbound_correlation_id(client: TestClient, bad_id: str) -> None:
    response = client.post("/chat", json=CHAT_BODY, headers={"x-request-id": bad_id})

    correlation_id = response.headers["x-request-id"]
    assert correlation_id != bad_id
    assert CORRELATION_ID_RE.fullmatch(correlation_id)


def test_independent_requests_get_distinct_ids(client: TestClient) -> None:
    first = client.post("/chat", json=CHAT_BODY)
    second = client.post("/chat", json=CHAT_BODY)

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_header_matches_correlation_id_in_body(client: TestClient) -> None:
    response = client.post("/chat", json=CHAT_BODY)

    assert response.headers["x-request-id"] == response.json()["correlation_id"]


def test_exposes_response_time_header(client: TestClient) -> None:
    response = client.post("/chat", json=CHAT_BODY)

    assert float(response.headers["x-response-time-ms"]) >= 0


def test_correlation_id_present_on_non_chat_routes(client: TestClient) -> None:
    response = client.get("/health")

    assert CORRELATION_ID_RE.fullmatch(response.headers["x-request-id"])
