"""Watchlist management endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

router = APIRouter()

# In-memory store for MVP (replace with Supabase in production)
_watchlist: dict[str, dict] = {}
_watchlist_counter = 0


class WatchlistAddRequest(BaseModel):
    """Request to add item to watchlist."""

    user_email: EmailStr
    product_id: str
    shop_id: str
    product_name: str
    product_url: str
    image_url: Optional[str] = None
    current_price: float
    currency: str = "SEK"
    target_price: Optional[float] = Field(None, description="Alert when price drops below this")
    notify_any_drop: bool = Field(True, description="Alert on any price drop")


class WatchlistItem(BaseModel):
    """Watchlist item response."""

    id: str
    user_email: str
    product_id: str
    shop_id: str
    product_name: str
    product_url: str
    image_url: Optional[str]
    price_at_add: float
    current_price: float
    lowest_price_seen: float
    currency: str
    target_price: Optional[float]
    notify_any_drop: bool
    price_change_percent: float
    created_at: str
    is_active: bool


class WatchlistResponse(BaseModel):
    """Watchlist response."""

    items: list[WatchlistItem]
    total: int


@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(request: WatchlistAddRequest):
    """Add an item to the user's watchlist."""
    global _watchlist_counter

    # Check for duplicates
    for item in _watchlist.values():
        if (
            item["user_email"] == request.user_email
            and item["product_id"] == request.product_id
            and item["shop_id"] == request.shop_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Item already in watchlist",
            )

    _watchlist_counter += 1
    item_id = str(_watchlist_counter)

    item = {
        "id": item_id,
        "user_email": request.user_email,
        "product_id": request.product_id,
        "shop_id": request.shop_id,
        "product_name": request.product_name,
        "product_url": request.product_url,
        "image_url": request.image_url,
        "price_at_add": request.current_price,
        "current_price": request.current_price,
        "lowest_price_seen": request.current_price,
        "currency": request.currency,
        "target_price": request.target_price,
        "notify_any_drop": request.notify_any_drop,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
    }

    _watchlist[item_id] = item

    return WatchlistItem(
        **item,
        price_change_percent=0.0,
    )


@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(user_email: str):
    """Get user's watchlist."""
    items = [
        item for item in _watchlist.values()
        if item["user_email"] == user_email and item["is_active"]
    ]

    response_items = []
    for item in items:
        price_change = (
            (item["current_price"] - item["price_at_add"]) / item["price_at_add"] * 100
            if item["price_at_add"] > 0
            else 0
        )
        response_items.append(
            WatchlistItem(
                **item,
                price_change_percent=round(price_change, 2),
            )
        )

    return WatchlistResponse(items=response_items, total=len(response_items))


@router.get("/watchlist/{item_id}", response_model=WatchlistItem)
async def get_watchlist_item(item_id: str):
    """Get a specific watchlist item."""
    item = _watchlist.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    price_change = (
        (item["current_price"] - item["price_at_add"]) / item["price_at_add"] * 100
        if item["price_at_add"] > 0
        else 0
    )

    return WatchlistItem(
        **item,
        price_change_percent=round(price_change, 2),
    )


@router.patch("/watchlist/{item_id}")
async def update_watchlist_item(
    item_id: str,
    target_price: Optional[float] = None,
    notify_any_drop: Optional[bool] = None,
):
    """Update watchlist item settings."""
    item = _watchlist.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if target_price is not None:
        item["target_price"] = target_price

    if notify_any_drop is not None:
        item["notify_any_drop"] = notify_any_drop

    price_change = (
        (item["current_price"] - item["price_at_add"]) / item["price_at_add"] * 100
        if item["price_at_add"] > 0
        else 0
    )

    return WatchlistItem(
        **item,
        price_change_percent=round(price_change, 2),
    )


@router.delete("/watchlist/{item_id}")
async def remove_from_watchlist(item_id: str):
    """Remove item from watchlist."""
    item = _watchlist.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Soft delete
    item["is_active"] = False

    return {"message": "Item removed from watchlist"}


@router.post("/watchlist/{item_id}/update-price")
async def update_item_price(item_id: str, new_price: float):
    """
    Update the current price of a watchlist item.

    Called by the price monitoring system.
    """
    item = _watchlist.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    old_price = item["current_price"]
    item["current_price"] = new_price

    if new_price < item["lowest_price_seen"]:
        item["lowest_price_seen"] = new_price

    return {
        "old_price": old_price,
        "new_price": new_price,
        "price_dropped": new_price < old_price,
        "lowest_price_seen": item["lowest_price_seen"],
    }
