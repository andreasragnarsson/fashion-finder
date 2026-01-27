"""Price checker for watchlist items."""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from src.shops.registry import ShopRegistry
from src.core.cost_calculator import get_cost_calculator


@dataclass
class PriceCheck:
    """Result of a price check."""

    watchlist_id: str
    product_id: str
    shop_id: str
    old_price: Decimal
    new_price: Decimal
    currency: str
    price_dropped: bool
    drop_amount: Decimal
    drop_percent: float
    target_price_reached: bool
    checked_at: datetime


class PriceChecker:
    """Check prices for watchlist items."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.getenv("API_URL", "http://localhost:8000")

    async def get_watchlist_items(self) -> list[dict]:
        """
        Fetch all active watchlist items.

        In production, this would query the database directly.
        For MVP, we call the API (which uses in-memory store).
        """
        # This would need to iterate through all users
        # For MVP, we'll just return an empty list and let the
        # API handle individual user watchlists
        return []

    async def check_price(self, item: dict) -> Optional[PriceCheck]:
        """
        Check current price for a watchlist item.

        Args:
            item: Watchlist item dict with product_id, shop_id, current_price, etc.

        Returns:
            PriceCheck result or None if check failed
        """
        shop_id = item.get("shop_id")
        product_id = item.get("product_id")

        adapter = ShopRegistry.get_adapter(shop_id)
        if not adapter:
            return None

        try:
            in_stock, current_price = await adapter.check_availability(product_id)

            if current_price is None:
                return None

            old_price = Decimal(str(item.get("current_price", 0)))
            new_price = current_price
            drop_amount = old_price - new_price
            drop_percent = float(drop_amount / old_price * 100) if old_price > 0 else 0

            target_price = item.get("target_price")
            target_reached = target_price is not None and new_price <= Decimal(str(target_price))

            return PriceCheck(
                watchlist_id=item.get("id", ""),
                product_id=product_id,
                shop_id=shop_id,
                old_price=old_price,
                new_price=new_price,
                currency=item.get("currency", "SEK"),
                price_dropped=new_price < old_price,
                drop_amount=drop_amount,
                drop_percent=drop_percent,
                target_price_reached=target_reached,
                checked_at=datetime.utcnow(),
            )

        except Exception as e:
            print(f"Error checking price for {shop_id}/{product_id}: {e}")
            return None

    async def check_all_items(self, items: list[dict]) -> list[PriceCheck]:
        """
        Check prices for multiple watchlist items.

        Args:
            items: List of watchlist items

        Returns:
            List of PriceCheck results for items with changes
        """
        results = []

        # Process in batches to respect rate limits
        batch_size = 10
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # Check batch in parallel
            checks = await asyncio.gather(
                *[self.check_price(item) for item in batch],
                return_exceptions=True,
            )

            for check in checks:
                if isinstance(check, PriceCheck):
                    results.append(check)

            # Delay between batches
            if i + batch_size < len(items):
                await asyncio.sleep(1)

        return results

    async def update_prices_via_api(self, checks: list[PriceCheck]) -> list[dict]:
        """
        Update prices in the system via API.

        Args:
            checks: List of price checks to update

        Returns:
            List of update results
        """
        results = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for check in checks:
                try:
                    response = await client.post(
                        f"{self.api_url}/api/watchlist/{check.watchlist_id}/update-price",
                        params={"new_price": float(check.new_price)},
                    )

                    if response.status_code == 200:
                        results.append({
                            "watchlist_id": check.watchlist_id,
                            "success": True,
                            "data": response.json(),
                        })
                    else:
                        results.append({
                            "watchlist_id": check.watchlist_id,
                            "success": False,
                            "error": response.text,
                        })

                except Exception as e:
                    results.append({
                        "watchlist_id": check.watchlist_id,
                        "success": False,
                        "error": str(e),
                    })

        return results


async def run_price_check():
    """Run a full price check cycle."""
    checker = PriceChecker()

    # In production, fetch from database
    # For MVP, this would need to be called with specific items
    print("Price checker initialized")
    print("In production, this would:")
    print("1. Fetch all active watchlist items from database")
    print("2. Check current prices for each item")
    print("3. Update prices and trigger notifications")

    return []


if __name__ == "__main__":
    asyncio.run(run_price_check())
