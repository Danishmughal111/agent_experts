"""Quick import test for all new strategy modules."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("Testing imports...")
import app.models
print("  [OK] models")
import app.strategies.base
print("  [OK] strategies.base")
import app.strategies.scheduler
print("  [OK] strategies.scheduler")
import app.strategies.digital_products
print("  [OK] strategies.digital_products")
import app.strategies.coding_agent
print("  [OK] strategies.coding_agent")
import app.strategies.content
print("  [OK] strategies.content")
import app.strategies.trading
print("  [OK] strategies.trading")
import app.strategies.freelance
print("  [OK] strategies.freelance")
import app.strategies.business
print("  [OK] strategies.business")
import app.api.strategies
print("  [OK] api.strategies")
print("")
print("ALL IMPORTS PASSED!")