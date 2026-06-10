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

def create_personal_token(subject: str, qtest_token_encrypted: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.token_ttl_minutes)).timestamp()),
        "scope": "qtest:mcp:safe",
        "qtest_token": qtest_token_encrypted,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def verify_personal_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
