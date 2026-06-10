from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "qtest-mcp-server"
    app_env: str = "dev"
    qtest_base_url: str
    qtest_client_auth_token: str
    jwt_secret: str
    fernet_key: str
    allowed_origins: str = ""
    token_ttl_minutes: int = 43200
    jwt_issuer: str = "qtest-mcp-server"
    jwt_audience: str = "qtest-mcp-clients"
    mcp_policy_file: str = ""
    mcp_policy_json: str = ""
    allow_bot_writes: bool = False
    default_user_scopes: str = "projects:read,requirements:read,requirements:write,testcases:read,testcases:write,testruns:read,defects:read,defects:write"
    default_bot_scopes: str = "projects:read,requirements:read,testcases:read,testruns:read,defects:read"
    mcp_admin_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
