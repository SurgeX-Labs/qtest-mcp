from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from cryptography.fernet import Fernet
from app.core.settings import settings

fernet = Fernet(settings.fernet_key.encode())

def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()

def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def create_access_token(
    subject: str,
    qtest_token_encrypted: str,
    token_type: str = "user",
    scopes: list[str] | None = None,
    ttl_minutes: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    resolved_scopes = scopes or _split_csv(settings.default_user_scopes)
    if token_type == "bot" and scopes is None:
        resolved_scopes = _split_csv(settings.default_bot_scopes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes or settings.token_ttl_minutes)).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "token_type": token_type,
        "scopes": resolved_scopes,
        "scope": "qtest:mcp:safe",
        "qtest_token": qtest_token_encrypted,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_personal_token(subject: str, qtest_token_encrypted: str) -> str:
    return create_access_token(
        subject=subject,
        qtest_token_encrypted=qtest_token_encrypted,
        token_type="user",
        scopes=_split_csv(settings.default_user_scopes),
    )


def verify_personal_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.InvalidTokenError:
        # Backward compatibility for tokens minted before aud/iss claims.
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
