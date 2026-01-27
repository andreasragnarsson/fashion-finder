"""Shop adapter modules for Fashion Finder."""

from .base import ShopAdapter, ShopConfig, ShopRegion, ProductResult, SearchQuery
from .registry import ShopRegistry

__all__ = [
    "ShopAdapter",
    "ShopConfig",
    "ShopRegion",
    "ProductResult",
    "SearchQuery",
    "ShopRegistry",
]
