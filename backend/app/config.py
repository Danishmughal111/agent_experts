"""Application settings loaded from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    openai_api_key: str = ""
    openai_model: str = "deepseek-chat"
    openai_base_url: str = "https://api.deepseek.com"
    database_url: str = "sqlite:///./dev.db"
    secret_key: str = "change-me"
    owner_password: str = "change123"
    agent_token: str = "agent-secret"
    base_currency: str = "USD"
    initial_balance: float = 1000.0
    daily_loss_limit_pct: float = 10.0
    total_loss_limit_pct: float = 20.0
    max_trade_size_pct: float = 10.0
    min_balance_threshold: float = 200.0
    payoneer_api_key: str = ""
    payoneer_account_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
