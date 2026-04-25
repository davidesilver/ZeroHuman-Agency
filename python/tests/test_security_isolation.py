"""Security Isolation Test Suite — Phase D.

Verify that multi-brand isolation is maintained and the hardcoded BRAND_ID
is no longer in effect.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


class TestBrandIsolation:
    def setup_method(self):
        import sys, os
        from pathlib import Path
        src_path = str(Path(__file__).parent.parent / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_get_brand_id_extracts_from_jwt_state(self):
        """Verify that _get_brand_id correctly fetches from request.state.brand_id."""
        from content_engine.api.routes import _get_brand_id

        mock_request = MagicMock()
        mock_request.state.brand_id = "brand-uuid-123"

        brand_id = _get_brand_id(mock_request)
        assert brand_id == "brand-uuid-123"

    def test_get_brand_id_raises_401_if_missing(self):
        """Verify that missing brand_id enforces a 401 error."""
        from content_engine.api.routes import _get_brand_id

        mock_request = MagicMock()
        # Explicitly remove it to simulate unpopulated state
        del mock_request.state.brand_id 

        with pytest.raises(HTTPException) as exc_info:
            _get_brand_id(mock_request)
        
        assert exc_info.value.status_code == 401

    def test_get_client_db_uses_jwt_when_available(self):
        """Verify RLS enforcement: it should use get_user_db when JWT is present."""
        from content_engine.api.routes import _get_client_db
        import content_engine.api.routes as routes_module

        # Mock get_user_db
        mock_user_db = MagicMock()
        mock_get_user_db = MagicMock(return_value=mock_user_db)
        routes_module.get_user_db = mock_get_user_db

        mock_request = MagicMock()
        mock_request.state.jwt = "fake-jwt-token"

        db = _get_client_db(mock_request)
        
        mock_get_user_db.assert_called_once_with("fake-jwt-token")
        assert db == mock_user_db

    def test_get_client_db_falls_back_to_service_role_without_jwt(self):
        """Scheduler/Cron routes don't have JWT, they should fallback to service role."""
        from content_engine.api.routes import _get_client_db
        import content_engine.api.routes as routes_module

        # Mock get_db
        mock_service_db = MagicMock()
        mock_get_db = MagicMock(return_value=mock_service_db)
        routes_module.get_db = mock_get_db

        mock_request = MagicMock()
        # Explicitly remove JWT
        del mock_request.state.jwt

        db = _get_client_db(mock_request)
        
        mock_get_db.assert_called_once()
        assert db == mock_service_db

    def test_scheduler_brand_id_extraction(self):
        """Verify scheduler extracts system BRAND_ID from env."""
        import os
        from content_engine.api.routes import _get_scheduler_brand_id
        import content_engine.api.routes as routes_module
        
        # Mock env variable extraction at runtime
        routes_module._SCHEDULER_BRAND_ID = "cron-brand-456"
        
        brand_id = _get_scheduler_brand_id()
        assert brand_id == "cron-brand-456"
        
        # Test missing failure
        routes_module._SCHEDULER_BRAND_ID = ""
        with pytest.raises(HTTPException) as exc_info:
            _get_scheduler_brand_id()
        assert exc_info.value.status_code == 503

    def test_scheduler_brand_ids_uses_override_when_present(self):
        """Explicit env override should still scope cron to a single brand."""
        from content_engine.api.routes import _get_scheduler_brand_ids
        import content_engine.api.routes as routes_module

        routes_module._SCHEDULER_BRAND_ID = "cron-brand-456"
        assert _get_scheduler_brand_ids() == ["cron-brand-456"]

    def test_scheduler_brand_ids_refuses_without_explicit_opt_in(self):
        """Audit P0-2: missing SCHEDULER_BRAND_ID *and* missing
        SCHEDULER_ALLOW_ALL_BRANDS must hard-fail rather than silently iterate
        across every tenant — otherwise a misconfigured deploy leaks across
        brands.
        """
        from content_engine.api.routes import _get_scheduler_brand_ids
        import content_engine.api.routes as routes_module
        from fastapi import HTTPException

        routes_module._SCHEDULER_BRAND_ID = ""
        routes_module._SCHEDULER_ALLOW_ALL_BRANDS = False

        with pytest.raises(HTTPException) as exc_info:
            _get_scheduler_brand_ids()
        assert exc_info.value.status_code == 503

    def test_scheduler_brand_ids_reads_memberships_when_explicitly_allowed(self):
        """When the operator explicitly opts in via SCHEDULER_ALLOW_ALL_BRANDS,
        fanning out across brand_members is the documented multi-brand path."""
        from content_engine.api.routes import _get_scheduler_brand_ids
        import content_engine.api.routes as routes_module

        routes_module._SCHEDULER_BRAND_ID = ""
        routes_module._SCHEDULER_ALLOW_ALL_BRANDS = True
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value.data = [
            {"brand_id": "brand-b"},
            {"brand_id": "brand-a"},
            {"brand_id": "brand-a"},
        ]
        routes_module.get_db = MagicMock(return_value=mock_db)

        try:
            assert _get_scheduler_brand_ids() == ["brand-a", "brand-b"]
        finally:
            routes_module._SCHEDULER_ALLOW_ALL_BRANDS = False
