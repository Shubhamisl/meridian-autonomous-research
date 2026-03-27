from fastapi import HTTPException

from src.meridian.infrastructure.auth import firebase_auth


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


def test_firebase_setup_state_marks_missing_admin_credentials(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    setup = firebase_auth.describe_firebase_setup()
    assert setup["admin_credentials_available"] is False
    assert "GOOGLE_APPLICATION_CREDENTIALS" in setup["message"]
