import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_pii_redaction() -> None:
    log_path = os.getenv("LOG_PATH", "data/logs.jsonl")
    
    response = client.post(
        "/chat",
        json={
            "user_id": "u-456",
            "session_id": "s-456",
            "feature": "test",
            "message": "My email is student@vinuni.edu.vn and my card is 4111 1111 1111 1111"
        }
    )
    
    assert response.status_code == 200
    
    found_log = False
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry.get("event") == "request_received" and log_entry.get("session_id") == "s-456":
                found_log = True
                payload_str = str(log_entry.get("payload", ""))
                assert "student@" not in payload_str
                assert "4111" not in payload_str
                assert "REDACTED_EMAIL" in payload_str
                assert "REDACTED_CREDIT_CARD" in payload_str
    
    assert found_log, "Log entry not found in logs.jsonl"
