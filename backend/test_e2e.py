"""End-to-end API test for AI Earning Machine."""
import sys
import json
import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
results = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((name, status, detail))
    print(f"  [{status}] {name}" + (f" - {detail}" if detail else ""))


def run():
    client = httpx.Client(timeout=30.0)

    # 1. Health
    try:
        r = client.get(f"{BASE}/health")
        check("health", r.status_code == 200 and r.json()["status"] == "ok")
    except Exception as e:
        check("health", False, str(e))

    # 2. Login
    try:
        r = client.post(f"{BASE}/login", json={"password": "change123"})
        token = r.json().get("token")
        check("login", r.status_code == 200 and token, "token received")
    except Exception as e:
        token = None
        check("login", False, str(e))

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Balance (owner)
    try:
        r = client.get(f"{BASE}/api/balance", headers=headers)
        check("balance", r.status_code == 200, f"balance={r.json().get('allocated_balance')}")
    except Exception as e:
        check("balance", False, str(e))

    # 4. List strategies
    try:
        r = client.get(f"{BASE}/api/strategies", headers=headers)
        data = r.json()
        check("strategies", r.status_code == 200 and len(data) >= 6,
              f"{len(data)} strategies")
    except Exception as e:
        check("strategies", False, str(e))

    # 5. Dashboard summary
    try:
        r = client.get(f"{BASE}/api/dashboard/summary", headers=headers)
        d = r.json()
        check("dashboard/summary", r.status_code == 200,
              f"revenue={d.get('total_revenue')}, strategies={len(d.get('strategies', []))}")
    except Exception as e:
        check("dashboard/summary", False, str(e))

    # 6. AI Decision
    try:
        r = client.get(f"{BASE}/api/strategies/decide", headers=headers)
        check("strategy/decide", r.status_code == 200,
              f"chose={r.json().get('strategy')}")
    except Exception as e:
        check("strategy/decide", False, str(e))

    # 7. Agent chat (agent token)
    try:
        r = client.post(f"{BASE}/chat",
                        headers={"X-Agent-Token": "agent-secret"},
                        json={"message": "test"})
        check("chat", r.status_code == 200, f"reply={r.json().get('reply', '')[:30]}")
    except Exception as e:
        check("chat", False, str(e))

    # 8. Run one strategy cycle
    try:
        r = client.post(f"{BASE}/api/strategies/run-cycle", headers=headers)
        d = r.json()
        check("run-cycle", r.status_code == 200, f"status={d.get('status')}")
    except Exception as e:
        check("run-cycle", False, str(e))

    # 9. Revenue
    try:
        r = client.get(f"{BASE}/api/revenue", headers=headers)
        check("revenue", r.status_code == 200)
    except Exception as e:
        check("revenue", False, str(e))

    # 10. Executions log
    try:
        r = client.get(f"{BASE}/api/strategies/executions", headers=headers)
        check("executions", r.status_code == 200)
    except Exception as e:
        check("executions", False, str(e))

    client.close()

    passed = sum(1 for _, s, _ in results if s == "PASS")
    total = len(results)
    print(f"\nRESULT: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)