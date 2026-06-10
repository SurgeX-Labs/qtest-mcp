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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
