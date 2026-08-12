"""Diagnose Supabase DB connection using separate DB_* fields."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.config import get_settings
from app.db import _build_database_url

s = get_settings()

print("=" * 60)
print("DB CONFIG VALUES (Render env se aayi hongi):")
print("=" * 60)
print("  DB_HOST     :", repr(s.db_host))
print("  DB_PORT     :", s.db_port)
print("  DB_NAME     :", s.db_name)
print("  DB_USER     :", s.db_user)
print("  DB_PASSWORD :", ("***" if s.db_password else "(KHALI)"))

print()
print("=" * 60)
if not s.db_host:
    print("❌ DB_HOST khali hai — abhi SQLite use hogi.")
    print("   Render par DB_HOST set karo: aws-0-xxxx.pooler.supabase.com")
else:
    url = _build_database_url(s)
    print("✅ URL built successfully:")
    # Password ko chhupao
    masked = url
    if s.db_password:
        masked = url.replace(s.db_password, "***")
    print("  ", masked)
    print()
    if "@" in s.db_host:
        print("❌ DB_HOST mein '@' mat daalo — sirf host likho")
    print()

if s.db_host:
    print("Testing actual database connection...")
    print("=" * 60)
    from app.db import engine
    try:
        with engine.connect() as conn:
            print("✅ CONNECTION SUCCESS! Database theek se connect hui.")
    except Exception as e:
        msg = str(e)
        print("❌ CONNECTION FAILED:")
        for line in msg.split("\n"):
            line = line.strip()
            if any(k in line.lower() for k in ["password", "host", "translate", "failed", "tenant", "timeout"]):
                print("   ", line[:200])