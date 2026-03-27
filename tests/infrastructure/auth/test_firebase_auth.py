import importlib.util
import sys
import types
from pathlib import Path

from fastapi import HTTPException

from src.meridian.infrastructure.auth import firebase_auth


def _load_isolated_firebase_auth(monkeypatch, initialize_app, service_account_path=""):
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
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", service_account_path)

    module_name = "test_firebase_auth_isolated"
    module_path = Path(firebase_auth.__file__)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def test_get_current_user_returns_generic_503_when_firebase_admin_failed_to_initialize(
    monkeypatch,
):
    def initialize_app(*args, **kwargs):
        raise RuntimeError("boom")

    module = _load_isolated_firebase_auth(monkeypatch, initialize_app)

    class DummyCreds:
        credentials = "token"

    try:
        import anyio

        anyio.run(module.get_current_user, DummyCreds())
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Firebase Admin is not initialized in this environment"
    else:
        raise AssertionError("Expected HTTPException")


def test_firebase_setup_state_reports_sdk_init_and_credentials(monkeypatch):
    def initialize_app(*args, **kwargs):
        raise RuntimeError("boom")

    module = _load_isolated_firebase_auth(monkeypatch, initialize_app)
    setup = module.describe_firebase_setup()
    assert setup["auth_sdk_available"] is True
    assert setup["service_account_credentials_available"] is False
    assert setup["adc_may_be_used"] is True
    assert setup["firebase_admin_ready"] is False
    assert setup["admin_initialization_error"] == "RuntimeError: boom"
    assert "GOOGLE_APPLICATION_CREDENTIALS" in setup["message"]
