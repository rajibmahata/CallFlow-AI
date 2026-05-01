"""
Tests for Retell AI webhook handler — signature verification and event routing.
"""
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


RETELL_SECRET = "test_retell_webhook_secret"

CALL_STARTED_PAYLOAD = {
    "event": "call_started",
    "data": {
        "call_id": "retell_abc123",
        "agent_id": "agent_001",
        "from_number": "+919876543210",
        "to_number": "+14155551234",
    }
}

CALL_ENDED_PAYLOAD = {
    "event": "call_ended",
    "data": {
        "call_id": "retell_abc123",
        "duration_ms": 120000,
        "transcript": "Agent: Hello! User: Yes interested.",
        "recording_url": "https://storage.retell.ai/recordings/abc123.mp3",
        "call_analysis": {
            "call_summary": "Lead expressed interest in attending the seminar.",
        },
    }
}


def make_signature(payload_str: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()


class TestWebhooks:
    @patch.dict("os.environ", {"RETELL_WEBHOOK_SECRET": RETELL_SECRET})
    def test_missing_signature_rejected(self, client):
        response = client.post(
            "/webhook/retell",
            json=CALL_STARTED_PAYLOAD,
        )
        # Without signature header should fail (401 or 403)
        assert response.status_code in (401, 403, 400)

    def test_twilio_opt_out_detection(self):
        from app.services.sms_service import is_opt_out_message
        assert is_opt_out_message("STOP")
        assert is_opt_out_message("stop please")
        assert is_opt_out_message("Unsubscribe me")
        assert not is_opt_out_message("Yes I want to attend")
        assert not is_opt_out_message("Call me back tomorrow")

    def test_hmac_signature_format(self):
        """Verify our HMAC helper produces correct length."""
        body = json.dumps(CALL_STARTED_PAYLOAD)
        sig = make_signature(body, RETELL_SECRET)
        assert len(sig) == 64  # SHA-256 hex digest
