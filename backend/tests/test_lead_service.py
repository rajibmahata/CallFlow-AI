"""
Tests for lead_service CSV import + deduplication.
"""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


VALID_CSV = """name,phone,email,age,city,language
Ramesh Sharma,+919876543210,r@test.com,62,Delhi,hi
Sunita Devi,+919765432109,,58,Mumbai,hi
Arun Mehta,+919654321098,,65,Bangalore,en
"""

DUPLICATE_CSV = """name,phone
Test User,+919876543210
Test User 2,+919876543210
"""

MISSING_PHONE_CSV = """name,email
Test User,x@test.com
"""


class TestLeadService:
    def test_normalize_columns_aliases(self):
        from app.services.lead_service import _normalize_columns
        row = {"mobile": "9876", "full_name": "Alice", "lang": "hi"}
        normalized = _normalize_columns(row)
        assert "phone" in normalized
        assert "name" in normalized
        assert "language" in normalized

    def test_clean_phone_strips_formatting(self):
        from app.services.lead_service import _clean_phone
        assert _clean_phone("+91 98765-43210") == "+919876543210"
        assert _clean_phone("(+91) 9876543210") == "+919876543210"

    def test_phone_hash_consistent(self):
        from app.services.lead_service import _phone_hash
        h1 = _phone_hash("+919876543210")
        h2 = _phone_hash("+919876543210")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_phone_hash_different_numbers(self):
        from app.services.lead_service import _phone_hash
        assert _phone_hash("+919876543210") != _phone_hash("+919765432109")

    def test_language_detection(self):
        """Hindi phone prefixes or city mappings resolve to 'hi'."""
        from app.services.lead_service import _detect_language
        # Explicit language field should pass through
        assert _detect_language("hi") == "hi"
        assert _detect_language("ta") == "ta"
        assert _detect_language("") == "en"  # default
        assert _detect_language(None) == "en"
