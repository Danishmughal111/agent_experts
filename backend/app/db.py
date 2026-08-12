"""Database engine/session setup. Works with Supabase Postgres or local SQLite."""
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base


def _build_database_url(settings) -> str:
    """Build a SQLAlchemy database URL.

    Priority:
    1. If db_host is set, build a PostgreSQL URL from SEPARATE parts
       (db_host, db_user, db_password, db_port, db_name). This avoids
       URL-format mistakes entirely.
    2. Otherwise use database_url as-is (e.g. sqlite default).
    """
    if settings.db_host:
        user = quote_plus(settings.db_user or "postgres")
        password = quote_plus(settings.db_password or "")
        host = settings.db_host
        port = settings.db_port or "5432"
        name = settings.db_name or "postgres"
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # default_config placeholder from pydantic: sqlite in dev
    return settings.database_url


def _engine():
    settings = get_settings()
    url = _build_database_url(settings)
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif url.startswith("postgres"):
        # Supabase/PostgreSQL requires SSL
        kwargs["connect_args"] = {"sslmode": "require", "connect_timeout": 30}
    engine = create_engine(url, **kwargs)
    return engine


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    # Import models so they register on Base.metadata.
    import app.models  # noqa F401
    Base.metadata.create_all(bind=engine)
