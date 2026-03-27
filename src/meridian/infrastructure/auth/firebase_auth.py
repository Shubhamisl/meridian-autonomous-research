import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import firebase_admin
    from firebase_admin import credentials, auth
except ImportError:
    firebase_admin = None
    credentials = None
    auth = None


_firebase_admin_service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
_firebase_admin_service_account_available = bool(
    _firebase_admin_service_account_path
    and os.path.exists(_firebase_admin_service_account_path)
)
_firebase_admin_initialization_succeeded = False
_firebase_admin_initialization_error = None


def _format_initialization_error(exc: Exception) -> str:
    detail = str(exc)
    if detail:
        return f"{exc.__class__.__name__}: {detail}"
    return exc.__class__.__name__


def describe_firebase_setup() -> dict[str, object]:
    adc_may_be_used = bool(
        firebase_admin is not None and not _firebase_admin_service_account_available
    )
    return {
        "auth_sdk_available": auth is not None,
        "service_account_credentials_available": _firebase_admin_service_account_available,
        "adc_may_be_used": adc_may_be_used,
        "firebase_admin_ready": _firebase_admin_initialization_succeeded,
        "admin_initialization_error": _firebase_admin_initialization_error,
        "message": (
            "Firebase Admin is configured."
            if _firebase_admin_initialization_succeeded
            else (
                "Firebase Admin could not initialize with the configured service account."
                if _firebase_admin_service_account_available
                else "Firebase Admin requires GOOGLE_APPLICATION_CREDENTIALS or valid ADC."
            )
        ),
    }


def _initialize_firebase_admin() -> None:
    global _firebase_admin_initialization_succeeded
    global _firebase_admin_initialization_error

    if firebase_admin is None or firebase_admin._apps:
        _firebase_admin_initialization_succeeded = firebase_admin is not None and bool(
            firebase_admin._apps
        )
        return

    try:
        if _firebase_admin_service_account_available:
            cred = credentials.Certificate(_firebase_admin_service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Falls back to Application Default Credentials.
            firebase_admin.initialize_app()
        _firebase_admin_initialization_succeeded = True
        _firebase_admin_initialization_error = None
    except Exception as exc:
        # Leave Firebase Admin uninitialized so runtime checks can report setup issues.
        _firebase_admin_initialization_succeeded = False
        _firebase_admin_initialization_error = _format_initialization_error(exc)
        return


_initialize_firebase_admin()

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify Firebase JWT and return user info."""
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase auth is not available in this environment",
        )
    if not _firebase_admin_initialization_succeeded:
        detail = "Firebase Admin is not initialized in this environment"
        if _firebase_admin_initialization_error:
            detail = f"{detail}: {_firebase_admin_initialization_error}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
