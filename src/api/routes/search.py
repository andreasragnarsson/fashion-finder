"""Product search endpoint."""

import asyncio
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.shops.base import SearchQuery, ProductResult
from src.shops.registry import ShopRegistry
from src.core.cost_calculator import get_cost_calculator

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(..., min_length=1, description="Search query")
    category: Optional[str] = Field(None, description="Product category filter")
    brand: Optional[str] = Field(None, description="Brand filter")
    color: Optional[str] = Field(None, description="Color filter")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    size: Optional[str] = Field(None, description="Size filter")
    gender: Optional[str] = Field(None, description="Gender filter")
    style_tags: list[str] = Field(default_factory=list, description="Style tags")
    shops: Optional[list[str]] = Field(None, description="Limit to specific shop IDs")
    limit: int = Field(20, ge=1, le=100, description="Max results per shop")
    include_costs: bool = Field(True, description="Calculate total costs")


class ProductResponse(BaseModel):
    """Product response model."""

    shop_id: str
    shop_name: str
    external_id: str
    name: str
    brand: Optional[str]
    price: float
    currency: str
    original_price: Optional[float]
    category: Optional[str]
    color: Optional[str]
    sizes: list[str]
    product_url: str
    affiliate_url: Optional[str]
    image_url: Optional[str]
    in_stock: bool
    relevance_score: float

    # Cost breakdown
    shipping_cost: Optional[float]
    customs_cost: Optional[float]
    vat_cost: Optional[float]
    total_cost: Optional[float]
    total_cost_sek: Optional[float]


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    total_results: int
    results: list[ProductResponse]


@router.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    Search for products across configured shops.

    Returns results from all shops sorted by relevance.
    """
    # Build search query
    search_query = SearchQuery(
        query=request.query,
        category=request.category,
        brand=request.brand,
        color=request.color,
        min_price=Decimal(str(request.min_price)) if request.min_price else None,
        max_price=Decimal(str(request.max_price)) if request.max_price else None,
        size=request.size,
        gender=request.gender,
        style_tags=request.style_tags,
        limit=request.limit,
    )

    # Get adapters
    if request.shops:
        adapters = [
            ShopRegistry.get_adapter(shop_id)
            for shop_id in request.shops
            if ShopRegistry.get_adapter(shop_id)
        ]
    else:
        adapters = ShopRegistry.get_all_adapters()

    if not adapters:
        raise HTTPException(status_code=400, detail="No shops configured")

    # Search all shops in parallel
    async def search_shop(adapter):
        try:
            return await adapter.search(search_query)
        except Exception as e:
            print(f"Error searching {adapter.shop_id}: {e}")
            return []

    results_lists = await asyncio.gather(*[search_shop(a) for a in adapters])

    # Flatten results
    all_results: list[ProductResult] = []
    for results in results_lists:
        all_results.extend(results)

    # Calculate costs if requested
    if request.include_costs and all_results:
        calculator = get_cost_calculator()

        async def add_costs(product: ProductResult) -> ProductResult:
            config = ShopRegistry.get_config(product.shop_id)
            if config:
                return await calculator.calculate_total_cost(product, config)
            return product

        all_results = await asyncio.gather(*[add_costs(p) for p in all_results])

    # Sort by relevance, then by total cost
    all_results.sort(
        key=lambda p: (-p.relevance_score, float(p.total_cost_sek or p.price))
    )

    # Build response
    return SearchResponse(
        query=request.query,
        total_results=len(all_results),
        results=[
            ProductResponse(
                shop_id=p.shop_id,
                shop_name=ShopRegistry.get_config(p.shop_id).display_name
                if ShopRegistry.get_config(p.shop_id)
                else p.shop_id,
                external_id=p.external_id,
                name=p.name,
                brand=p.brand,
                price=float(p.price),
                currency=p.currency,
                original_price=float(p.original_price) if p.original_price else None,
                category=p.category,
                color=p.color,
                sizes=p.sizes,
                product_url=p.product_url,
                affiliate_url=p.affiliate_url,
                image_url=p.image_url,
                in_stock=p.in_stock,
                relevance_score=p.relevance_score,
                shipping_cost=float(p.shipping_cost) if p.shipping_cost else None,
                customs_cost=float(p.customs_cost) if p.customs_cost else None,
                vat_cost=float(p.vat_cost) if p.vat_cost else None,
                total_cost=float(p.total_cost) if p.total_cost else None,
                total_cost_sek=float(p.total_cost_sek) if p.total_cost_sek else None,
            )
            for p in all_results
        ],
    )


@router.get("/search/suggestions")
async def search_suggestions(q: str, limit: int = 5):
    """
    Get search suggestions based on partial query.

    Returns common search terms and brand names.
    """
    # This would typically query an index of popular searches
    # For MVP, return empty list
    return {"suggestions": []}
