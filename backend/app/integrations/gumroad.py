"""Real Gumroad v2 API integration.

This makes the agent actually SELL digital products (not just generate them).
With a free Gumroad account + access token, the agent can:
  1. Create a real, live product listing on Gumroad
  2. Get a shareable checkout URL that accepts real payments
  3. Automatically update/enable the product

Gumroad docs:
  - https://app.gumroad.com/api
  - Token: https://app.gumroad.com/settings/advanced#application-form

The ONLY human step required is: create a Gumroad account and paste the
GUMROAD_ACCESS_TOKEN into the environment. Everything else is automated.
"""
from __future__ import annotations

import httpx

BASE_URL = "https://api.gumroad.com/v2"


class GumroadError(Exception):
    """Raised when Gumroad API returns an error."""


class GumroadClient:
    """Minimal, dependency-light Gumroad v2 client (uses httpx only)."""

    def __init__(self, access_token: str):
        if not access_token:
            raise GumroadError(
                "GUMROAD_ACCESS_TOKEN is empty. Set it in the backend environment "
                "to enable real product selling."
            )
        self.token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{BASE_URL}{path}"
        try:
            resp = httpx.request(
                method, url, headers=self.headers, timeout=30.0, **kwargs
            )
        except httpx.HTTPError as e:
            raise GumroadError(f"Could not reach Gumroad: {e}") from e

        if resp.status_code >= 400:
            raise GumroadError(
                f"Gumroad error {resp.status_code}: {resp.text[:300]}"
            )

        try:
            return resp.json()
        except Exception as e:
            raise GumroadError(f"Invalid Gumroad response: {e}") from e

    def create_product(
        self,
        name: str,
        description: str,
        price_cents: int,
        currency: str = "usd",
    ) -> dict:
        """Create a real product on Gumroad and return its live checkout URL.

        price_cents is the price in cents (e.g. 1900 = $19.00).
        """
        data = {
            "name": name,
            "description": description,
            "price": str(price_cents),
            "currency": currency,
        }
        result = self._request("POST", "/products", data=data)

        if not result.get("success"):
            raise GumroadError(f"Gumroad refused to create product: {result}")

        product = result.get("product", {})
        return {
            "gumroad_id": product.get("id"),
            "name": product.get("name"),
            "short_url": product.get("short_url"),  # shareable checkout link
            "formatted_price": product.get("formatted_price"),
            "preview_url": product.get("preview_url"),
        }

    def enable_product(self, gumroad_id: str) -> dict:
        """Enable a product so it is live and purchasable."""
        return self._request("PUT", f"/products/{gumroad_id}/enable")

    def list_products(self) -> list:
        """List all products for this Gumroad account."""
        result = self._request("GET", "/products")
        return result.get("products", [])

def dollars_to_cents(dollars: float) -> int:
    """Convert a dollar amount to Gumroad's cents integer."""
    return int(round(dollars * 100))


def get_client() -> GumroadClient:
    """Build a GumroadClient from app settings."""
    from app.config import get_settings

    settings = get_settings()
    return GumroadClient(settings.gumroad_access_token)