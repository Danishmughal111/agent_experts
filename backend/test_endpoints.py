"""End-to-end endpoint test using FastAPI TestClient (no live server needed)."""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

# Use an isolated temp DB so the test never pollutes dev.db
os.environ["DATABASE_URL"] = "sqlite:///./test_endpoints.db"

from fastapi.testclient import TestClient

from app.main import app

# Use the context manager so the lifespan (init_db + seed strategies) runs.
with TestClient(app) as client:
    print("=== /health ===")
    r = client.get("/health")
    print(r.status_code, r.json())

    print("=== /auto-login ===")
    r = client.get("/auto-login")
    print(r.status_code, "token_present:", bool(r.json().get("token")))

    token = r.json().get("token", "")
    headers = {"Authorization": f"Bearer {token}"}

    print("=== /api/strategies ===")
    r = client.get("/api/strategies", headers=headers)
    print(r.status_code)
    for s in r.json():
        print("  ", s["name"], "enabled=", s["enabled"], "risk=", s["risk_level"])

    print("=== /api/dashboard/summary ===")
    r = client.get("/api/dashboard/summary", headers=headers)
    print(r.status_code)
    print("  wallet:", r.json().get("wallet"))
    print("  stop_loss:", r.json().get("stop_loss"))

    print("=== /api/gumroad/webhook (sale) ===")
    r = client.post(
        "/api/gumroad/webhook",
        json={"gumroad_id": "test-123", "price": 19.99, "permalink": "https://gum.co/test"},
    )
    print(r.status_code, r.json())

    print("=== /api/dashboard/summary after sale ===")
    r = client.get("/api/dashboard/summary", headers=headers)
    print(r.status_code)
    print("  wallet:", r.json().get("wallet"))
    print("  total_revenue:", r.json().get("total_revenue"))

print("ALL_ENDPOINT_TESTS_DONE")
