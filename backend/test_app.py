"""Test app startup and route registration."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.main import app

routes = sorted(set(r.path for r in app.routes))
print(f"Total routes: {len(routes)}")
for r in routes:
    print(f"  {r}")
print("APP STARTUP OK!")