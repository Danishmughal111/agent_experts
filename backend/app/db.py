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
       URL-format mistakes entirely — the code joins the parts itself.
    2. Otherwise use database_url as-is (e.g. sqlite default for local dev).
    """
    if settings.db_host:
        host = (settings.db_host or "").strip()
        user = quote_plus((settings.db_user or "postgres").strip())
        password = quote_plus(settings.db_password or "")
        port = settings.db_port or "5432"
        name = settings.db_name or "postgres"
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    return settings.database_url


def _mask_url(url: str) -> str:
    """Return a log-safe version of the URL (password hidden)."""
    try:
        from sqlalchemy.engine import make_url
        u = make_url(url)
        if u.password:
            return url.replace(u.password, "***")
    except Exception:
        pass
    return url


def _engine():
    settings = get_settings()
    url = _build_database_url(settings)

    # Print a clear startup message so Render logs show exactly what is used.
    print("=" * 60, flush=True)
    if url.startswith("sqlite"):
        print("[DB] Using SQLite (local/dev mode)", flush=True)
    elif url.startswith("postgres"):
        print("[DB] Using PostgreSQL:", _mask_url(url), flush=True)
    print("=" * 60, flush=True)

    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif url.startswith("postgres"):
        # Supabase/PostgreSQL requires SSL
        kwargs["connect_args"] = {"sslmode": "require", "connect_timeout": 30}

    return create_engine(url, **kwargs)


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    # Import models so they register on Base.metadata.
    import app.models  # noqa F401
    Base.metadata.create_all(bind=engine)