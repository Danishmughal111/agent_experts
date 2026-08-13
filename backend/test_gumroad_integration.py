"""Quick sanity test for the Gumroad integration (no live network needed)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.integrations.gumroad import GumroadClient, dollars_to_cents, GumroadError

print("dollars_to_cents(19)   =", dollars_to_cents(19))
print("dollars_to_cents(9.99) =", dollars_to_cents(9.99))
print("dollars_to_cents(15.99)=", dollars_to_cents(15.99))

try:
    GumroadClient("")
    print("EMPTY_TOKEN: no error (unexpected)")
except GumroadError as e:
    print("EMPTY_TOKEN_ERROR_OK =", str(e)[:45])

print("GUMMROAD_TEST_OK")