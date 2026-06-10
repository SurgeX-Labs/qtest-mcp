from fastapi import APIRouter, Header, HTTPException
from app.models.auth import ServiceTokenRequest, TokenRequest, TokenResponse
from app.services.qtest_client import QTestClient
from app.core.security import create_access_token, create_personal_token, encrypt_secret
from app.core.settings import settings

router = APIRouter()

@router.post("/generate-token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    try:
        qtest_token = await QTestClient.login(request.username, request.password)
        encrypted = encrypt_secret(qtest_token)
        personal = create_personal_token(subject=request.username, qtest_token_encrypted=encrypted)
        return TokenResponse(personal_mcp_token=personal)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Unable to authenticate with qTest: {str(exc)}")


@router.post("/generate-service-token", response_model=TokenResponse)
async def generate_service_token(request: ServiceTokenRequest, x_admin_token: str | None = Header(default=None)):
    if not settings.mcp_admin_token:
        raise HTTPException(status_code=403, detail="Service token generation endpoint is disabled.")

    if x_admin_token != settings.mcp_admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")

    try:
        encrypted = encrypt_secret(request.qtest_bearer_token)
        personal = create_access_token(
            subject=request.subject,
            qtest_token_encrypted=encrypted,
            token_type=request.token_type,
            scopes=request.scopes,
            ttl_minutes=request.ttl_minutes,
        )
        return TokenResponse(personal_mcp_token=personal)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to generate service token: {str(exc)}")
