from pydantic import BaseModel, Field

class TokenRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class TokenResponse(BaseModel):
    personal_mcp_token: str
    token_type: str = "Bearer"
    mcp_url: str = "/mcp"
