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


def test_get_current_user_returns_503_when_firebase_admin_failed_to_initialize(
    monkeypatch,
):
    monkeypatch.setattr(firebase_auth, "auth", object())
    monkeypatch.setattr(
        firebase_auth, "_firebase_admin_initialization_succeeded", False
    )

    class DummyCreds:
        credentials = "token"

    try:
        import anyio

        anyio.run(firebase_auth.get_current_user, DummyCreds())
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Firebase Admin is not initialized" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")


def test_firebase_setup_state_reports_sdk_init_and_credentials(monkeypatch):
    class DummyFirebaseAdmin:
        pass

    monkeypatch.setattr(firebase_auth, "firebase_admin", DummyFirebaseAdmin())
    monkeypatch.setattr(firebase_auth, "auth", object())
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(
        firebase_auth, "_firebase_admin_initialization_succeeded", False
    )
    setup = firebase_auth.describe_firebase_setup()
    assert setup["auth_sdk_available"] is True
    assert setup["service_account_credentials_available"] is False
    assert setup["adc_may_be_used"] is True
    assert setup["admin_initialization_succeeded"] is False
    assert setup["admin_credentials_available"] is False
    assert "GOOGLE_APPLICATION_CREDENTIALS" in setup["message"]
