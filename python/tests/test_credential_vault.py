import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

TEST_KEY = Fernet.generate_key().decode()

@pytest.fixture
def fernet_key(monkeypatch):
    monkeypatch.setenv("BRAND_SECRETS_ENCRYPTION_KEY", TEST_KEY)
    return TEST_KEY

@pytest.mark.asyncio
async def test_set_credentials_benchmark(fernet_key):
    from content_engine.services.credential_vault import set_credentials

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_execute = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute.return_value = mock_execute

    brand_id = str(uuid.uuid4())
    service_name = "test_service"

    # Generate many credentials to magnify the difference
    creds = {f"key_{i}": f"value_{i}" for i in range(100)}

    with patch("content_engine.services.credential_vault.get_db", return_value=mock_db):
        start_time = time.perf_counter()
        await set_credentials(brand_id, service_name, creds)
        end_time = time.perf_counter()

    execution_time = end_time - start_time
    print(f"\nExecution time for set_credentials: {execution_time:.4f}s")

    # In old version, upsert is called 100 times.
    # In new version, upsert is called 1 time.
    print(f"Upsert called {mock_table.upsert.call_count} times")
