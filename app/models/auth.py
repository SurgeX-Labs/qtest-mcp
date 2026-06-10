from pydantic import BaseModel, Field

class TokenRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class TokenResponse(BaseModel):
    personal_mcp_token: str
    token_type: str = "Bearer"
    mcp_url: str = "/mcp"


class ServiceTokenRequest(BaseModel):
    subject: str = Field(min_length=1)
    qtest_bearer_token: str = Field(min_length=1)
    token_type: str = Field(default="bot", pattern="^(bot|user)$")
    scopes: list[str] | None = None
    ttl_minutes: int | None = Field(default=None, gt=0)
