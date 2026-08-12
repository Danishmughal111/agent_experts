"""Test new features: auto-login + agent logs."""
import sys
import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"

print("Testing new features...")

# 1. Auto-login (no password)
r = httpx.get(f"{BASE}/auto-login")
token = r.json().get("token")
print(f"  [{'PASS' if r.status_code == 200 and token else 'FAIL'}] auto-login")

headers = {"Authorization": f"Bearer {token}"}

# 2. Agent logs endpoint
r = httpx.get(f"{BASE}/api/agent/logs", headers=headers)
logs = r.json()
print(f"  [{'PASS' if r.status_code == 200 and isinstance(logs, list) else 'FAIL'}] agent/logs - {len(logs)} entries")

# Show first few log entries
for log in logs[:5]:
    print(f"    - {log.get('action')} | {log.get('detail', '')[:60]}")

# 3. Verify logs contain our earlier activity
has_data = len(logs) > 0
print(f"  [{'PASS' if has_data else 'FAIL'}] logs contain activity data")

print("\nDONE")