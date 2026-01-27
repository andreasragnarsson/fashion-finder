"""Outfit management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

router = APIRouter()

# In-memory store for MVP (replace with Supabase in production)
_outfits: dict[str, dict] = {}
_outfit_counter = 0


class OutfitItemInput(BaseModel):
    """Input for an item within an outfit."""

    item_type: str
    description: str
    brand_guess: Optional[str] = None
    color: str
    style_tags: list[str] = Field(default_factory=list)
    size: Optional[str] = None
    selected_product_id: Optional[str] = None


class CreateOutfitRequest(BaseModel):
    """Request to create a new outfit."""

    user_email: EmailStr
    name: Optional[str] = None
    description: Optional[str] = None
    source_image_url: Optional[str] = None
    ai_analysis: Optional[dict] = None
    items: list[OutfitItemInput] = Field(default_factory=list)
    budget: Optional[float] = None
    budget_currency: str = "SEK"


class OutfitItemResponse(BaseModel):
    """Response for an outfit item."""

    id: str
    item_type: str
    description: str
    brand_guess: Optional[str]
    color: str
    style_tags: list[str]
    size: Optional[str]
    selected_product_id: Optional[str]


class OutfitResponse(BaseModel):
    """Response for an outfit."""

    id: str
    user_email: str
    name: Optional[str]
    description: Optional[str]
    source_image_url: Optional[str]
    items: list[OutfitItemResponse]
    budget: Optional[float]
    budget_currency: str
    created_at: str
    updated_at: str


class OutfitListResponse(BaseModel):
    """Response for listing outfits."""

    outfits: list[OutfitResponse]
    total: int


@router.post("/outfits", response_model=OutfitResponse)
async def create_outfit(request: CreateOutfitRequest):
    """Create a new outfit from identified items."""
    global _outfit_counter

    _outfit_counter += 1
    outfit_id = str(_outfit_counter)
    now = datetime.utcnow().isoformat()

    # Create outfit items
    items = []
    for idx, item in enumerate(request.items):
        items.append({
            "id": f"{outfit_id}_{idx}",
            "item_type": item.item_type,
            "description": item.description,
            "brand_guess": item.brand_guess,
            "color": item.color,
            "style_tags": item.style_tags,
            "size": item.size,
            "selected_product_id": item.selected_product_id,
        })

    outfit = {
        "id": outfit_id,
        "user_email": request.user_email,
        "name": request.name or f"Outfit {outfit_id}",
        "description": request.description,
        "source_image_url": request.source_image_url,
        "ai_analysis": request.ai_analysis,
        "items": items,
        "budget": request.budget,
        "budget_currency": request.budget_currency,
        "created_at": now,
        "updated_at": now,
    }

    _outfits[outfit_id] = outfit

    return OutfitResponse(
        id=outfit["id"],
        user_email=outfit["user_email"],
        name=outfit["name"],
        description=outfit["description"],
        source_image_url=outfit["source_image_url"],
        items=[OutfitItemResponse(**item) for item in items],
        budget=outfit["budget"],
        budget_currency=outfit["budget_currency"],
        created_at=outfit["created_at"],
        updated_at=outfit["updated_at"],
    )


@router.get("/outfits", response_model=OutfitListResponse)
async def list_outfits(user_email: str):
    """List user's saved outfits."""
    user_outfits = [
        outfit for outfit in _outfits.values()
        if outfit["user_email"] == user_email
    ]

    return OutfitListResponse(
        outfits=[
            OutfitResponse(
                id=o["id"],
                user_email=o["user_email"],
                name=o["name"],
                description=o["description"],
                source_image_url=o["source_image_url"],
                items=[OutfitItemResponse(**item) for item in o["items"]],
                budget=o["budget"],
                budget_currency=o["budget_currency"],
                created_at=o["created_at"],
                updated_at=o["updated_at"],
            )
            for o in user_outfits
        ],
        total=len(user_outfits),
    )


@router.get("/outfits/{outfit_id}", response_model=OutfitResponse)
async def get_outfit(outfit_id: str):
    """Get a specific outfit."""
    outfit = _outfits.get(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    return OutfitResponse(
        id=outfit["id"],
        user_email=outfit["user_email"],
        name=outfit["name"],
        description=outfit["description"],
        source_image_url=outfit["source_image_url"],
        items=[OutfitItemResponse(**item) for item in outfit["items"]],
        budget=outfit["budget"],
        budget_currency=outfit["budget_currency"],
        created_at=outfit["created_at"],
        updated_at=outfit["updated_at"],
    )


@router.patch("/outfits/{outfit_id}")
async def update_outfit(
    outfit_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    budget: Optional[float] = None,
):
    """Update outfit details."""
    outfit = _outfits.get(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    if name is not None:
        outfit["name"] = name
    if description is not None:
        outfit["description"] = description
    if budget is not None:
        outfit["budget"] = budget

    outfit["updated_at"] = datetime.utcnow().isoformat()

    return OutfitResponse(
        id=outfit["id"],
        user_email=outfit["user_email"],
        name=outfit["name"],
        description=outfit["description"],
        source_image_url=outfit["source_image_url"],
        items=[OutfitItemResponse(**item) for item in outfit["items"]],
        budget=outfit["budget"],
        budget_currency=outfit["budget_currency"],
        created_at=outfit["created_at"],
        updated_at=outfit["updated_at"],
    )


@router.patch("/outfits/{outfit_id}/items/{item_id}")
async def update_outfit_item(
    outfit_id: str,
    item_id: str,
    size: Optional[str] = None,
    selected_product_id: Optional[str] = None,
):
    """Update an item within an outfit (e.g., set size or select a product)."""
    outfit = _outfits.get(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    item = next((i for i in outfit["items"] if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if size is not None:
        item["size"] = size
    if selected_product_id is not None:
        item["selected_product_id"] = selected_product_id

    outfit["updated_at"] = datetime.utcnow().isoformat()

    return OutfitItemResponse(**item)


@router.delete("/outfits/{outfit_id}")
async def delete_outfit(outfit_id: str):
    """Delete an outfit."""
    if outfit_id not in _outfits:
        raise HTTPException(status_code=404, detail="Outfit not found")

    del _outfits[outfit_id]
    return {"message": "Outfit deleted"}
