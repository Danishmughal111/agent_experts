"""Application settings loaded from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    openai_api_key: str = ""
    openai_model: str = "deepseek-chat"
    openai_base_url: str = "https://api.deepseek.com"
    database_url: str = "sqlite:///./dev.db"
    # Separate DB connection parts (easier than a full URL)
    db_host: str = ""
    db_port: str = "5432"
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = ""
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
    # Trading API keys
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    binance_api_key: str = ""
    binance_secret_key: str = ""
    # Gumroad
    gumroad_access_token: str = ""
    gumroad_product_id: str = ""
    # Scheduler
    scheduler_interval_minutes: int = 10
    auto_approve_low_risk: bool = False
    # Strategy defaults
    trading_max_risk_pct: float = 10.0
    trading_max_per_trade_pct: float = 2.0
    content_auto_publish: bool = False
    freelance_auto_apply: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
