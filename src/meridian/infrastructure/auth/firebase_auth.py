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

def describe_firebase_setup() -> dict[str, object]:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    has_service_account = bool(cred_path and os.path.exists(cred_path))
    return {
        "auth_sdk_available": auth is not None,
        "admin_credentials_available": has_service_account,
        "message": (
            "Firebase Admin is configured."
            if has_service_account
            else "Firebase Admin requires GOOGLE_APPLICATION_CREDENTIALS or valid ADC."
        ),
    }


def _initialize_firebase_admin() -> None:
    if firebase_admin is None or firebase_admin._apps:
        return

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # Falls back to Application Default Credentials.
            firebase_admin.initialize_app()
    except Exception:
        # Leave Firebase Admin uninitialized so runtime checks can report setup issues.
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
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
