from fastapi import APIRouter, HTTPException
from app.models.auth import TokenRequest, TokenResponse
from app.services.qtest_client import QTestClient
from app.core.security import encrypt_secret, create_personal_token

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
