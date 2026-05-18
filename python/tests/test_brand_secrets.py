"""Unit tests for brand_secrets: encrypt/decrypt round-trip and cache invalidation."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet

# Generate a test key
TEST_KEY = Fernet.generate_key().decode()
TEST_BRAND = "brand-uuid-1234"


@pytest.fixture(autouse=True)
def clear_secret_cache():
    """Flush the in-memory cache before and after every test."""
    from content_engine.services import brand_secrets
    brand_secrets._cache.clear()
    yield
    brand_secrets._cache.clear()


@pytest.fixture
def fernet_key(monkeypatch):
    monkeypatch.setenv("BRAND_SECRETS_ENCRYPTION_KEY", TEST_KEY)
    # Reload settings so the new env var is picked up
    from content_engine import config
    monkeypatch.setattr(config.settings, "brand_secrets_encryption_key", TEST_KEY)
    return TEST_KEY


class TestEncryptDecryptRoundTrip:
    def test_roundtrip(self, fernet_key):
        from content_engine.services.brand_secrets import _fernet

        f = _fernet()
        plaintext = "super-secret-api-key-abc123"
        ciphertext = f.encrypt(plaintext.encode()).decode()
        recovered = f.decrypt(ciphertext.encode()).decode()
        assert recovered == plaintext

    def test_different_plaintexts_produce_different_ciphertexts(self, fernet_key):
        from content_engine.services.brand_secrets import _fernet

        f = _fernet()
        c1 = f.encrypt(b"key-a").decode()
        c2 = f.encrypt(b"key-b").decode()
        assert c1 != c2

    def test_fernet_raises_without_key(self, monkeypatch):
        from content_engine import config
        monkeypatch.setattr(config.settings, "brand_secrets_encryption_key", "")

        from content_engine.services.brand_secrets import _fernet
        with pytest.raises(RuntimeError, match="BRAND_SECRETS_ENCRYPTION_KEY"):
            _fernet()


class TestCacheInvalidation:
    def test_invalidate_clears_brand_entries(self, fernet_key):
        from content_engine.services import brand_secrets

        # Manually populate cache
        brand_secrets._cache[("brand-1", "brevo", "api_key")] = "val1"
        brand_secrets._cache[("brand-1", "heygen", "api_key")] = "val2"
        brand_secrets._cache[("brand-2", "brevo", "api_key")] = "val3"

        brand_secrets.invalidate_brand_cache("brand-1")

        assert ("brand-1", "brevo", "api_key") not in brand_secrets._cache
        assert ("brand-1", "heygen", "api_key") not in brand_secrets._cache
        # Other brand untouched
        assert ("brand-2", "brevo", "api_key") in brand_secrets._cache

    def test_get_brand_secret_uses_cache(self, fernet_key):
        from content_engine.services import brand_secrets

        brand_secrets._cache[(TEST_BRAND, "brevo", "api_key")] = "cached-value"

        # Should return from cache without hitting DB
        with patch("content_engine.services.brand_secrets.get_db") as mock_db:
            result = brand_secrets.get_brand_secret(TEST_BRAND, "brevo", "api_key")

        assert result == "cached-value"
        mock_db.assert_not_called()

    def test_get_brand_secret_returns_none_when_missing(self, fernet_key):
        from content_engine.services.brand_secrets import get_brand_secret

        mock_result = MagicMock()
        mock_result.data = None

        with patch("content_engine.services.brand_secrets.get_db") as mock_db:
            mock_db.return_value.from_.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
            result = get_brand_secret(TEST_BRAND, "brevo", "api_key")

        assert result is None
