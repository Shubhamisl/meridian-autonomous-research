import importlib
import sys
import types

from fastapi import HTTPException

from src.meridian.infrastructure.auth import firebase_auth


def _reload_firebase_auth_with_fake_admin(monkeypatch, initialize_app):
    fake_admin = types.ModuleType("firebase_admin")
    fake_admin._apps = []
    fake_admin.initialize_app = initialize_app
    fake_admin.credentials = types.SimpleNamespace(
        Certificate=lambda path: {"certificate_path": path}
    )
    fake_admin.auth = types.SimpleNamespace(
        verify_id_token=lambda token: {"uid": "uid", "email": "user@example.com"}
    )

    monkeypatch.setitem(sys.modules, "firebase_admin", fake_admin)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    return importlib.reload(firebase_auth)


def test_get_current_user_returns_503_when_auth_sdk_missing(monkeypatch):
    monkeypatch.setattr(firebase_auth, "auth", None)

    class DummyCreds:
        credentials = "token"

    try:
        import anyio

        anyio.run(firebase_auth.get_current_user, DummyCreds())
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Firebase auth is not available" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")


def test_get_current_user_returns_503_when_firebase_admin_failed_to_initialize(
    monkeypatch,
):
    def initialize_app(*args, **kwargs):
        raise RuntimeError("boom")

    module = _reload_firebase_auth_with_fake_admin(monkeypatch, initialize_app)

    class DummyCreds:
        credentials = "token"

    try:
        import anyio

        anyio.run(module.get_current_user, DummyCreds())
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Firebase Admin is not initialized" in exc.detail
        assert "RuntimeError: boom" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")


def test_firebase_setup_state_reports_sdk_init_and_credentials(monkeypatch):
    def initialize_app(*args, **kwargs):
        raise RuntimeError("boom")

    module = _reload_firebase_auth_with_fake_admin(monkeypatch, initialize_app)
    setup = module.describe_firebase_setup()
    assert setup["auth_sdk_available"] is True
    assert setup["service_account_credentials_available"] is False
    assert setup["adc_may_be_used"] is True
    assert setup["firebase_admin_ready"] is False
    assert setup["admin_initialization_error"] == "RuntimeError: boom"
    assert "GOOGLE_APPLICATION_CREDENTIALS" in setup["message"]
