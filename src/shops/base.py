"""Base shop adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class ShopRegion(str, Enum):
    SE = "SE"  # Sweden
    EU = "EU"  # European Union (non-Sweden)
    NON_EU = "NON_EU"  # Outside EU


@dataclass
class ShopConfig:
    """Configuration for a shop adapter."""

    id: str
    name: str
    display_name: str
    url: str
    region: ShopRegion = ShopRegion.EU
    currency: str = "SEK"
    trust_score: float = 0.8

    # Feed configuration
    feed_url: Optional[str] = None
    feed_type: Optional[str] = None  # "csv", "xml", "api"
    feed_mapping: dict = field(default_factory=dict)

    # Affiliate info
    affiliate_network: Optional[str] = None
    affiliate_id: Optional[str] = None
    affiliate_url_template: Optional[str] = None

    # Shipping info
    free_shipping_threshold: Optional[Decimal] = None
    base_shipping_cost: Optional[Decimal] = None
    ships_to_sweden: bool = True


@dataclass
class ProductResult:
    """A product result from a shop search."""

    shop_id: str
    external_id: str
    name: str
    brand: Optional[str]
    price: Decimal
    currency: str
    original_price: Optional[Decimal] = None

    # Product details
    category: Optional[str] = None
    color: Optional[str] = None
    sizes: list[str] = field(default_factory=list)
    material: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None

    # URLs
    product_url: str = ""
    affiliate_url: Optional[str] = None
    image_url: Optional[str] = None

    # Computed fields (filled by cost calculator)
    shipping_cost: Optional[Decimal] = None
    customs_cost: Optional[Decimal] = None
    vat_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    total_cost_sek: Optional[Decimal] = None

    # Metadata
    in_stock: bool = True
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "shop_id": self.shop_id,
            "external_id": self.external_id,
            "name": self.name,
            "brand": self.brand,
            "price": float(self.price) if self.price else None,
            "currency": self.currency,
            "original_price": float(self.original_price) if self.original_price else None,
            "category": self.category,
            "color": self.color,
            "sizes": self.sizes,
            "material": self.material,
            "gender": self.gender,
            "description": self.description,
            "product_url": self.product_url,
            "affiliate_url": self.affiliate_url,
            "image_url": self.image_url,
            "shipping_cost": float(self.shipping_cost) if self.shipping_cost else None,
            "customs_cost": float(self.customs_cost) if self.customs_cost else None,
            "vat_cost": float(self.vat_cost) if self.vat_cost else None,
            "total_cost": float(self.total_cost) if self.total_cost else None,
            "total_cost_sek": float(self.total_cost_sek) if self.total_cost_sek else None,
            "in_stock": self.in_stock,
            "relevance_score": self.relevance_score,
        }


@dataclass
class SearchQuery:
    """Search query parameters."""

    query: str
    category: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    size: Optional[str] = None
    gender: Optional[str] = None
    style_tags: list[str] = field(default_factory=list)
    limit: int = 20


class ShopAdapter(ABC):
    """Abstract base class for shop adapters."""

    def __init__(self, config: ShopConfig):
        self.config = config

    @property
    def shop_id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[ProductResult]:
        """
        Search the shop for products matching the query.

        Args:
            query: Search parameters

        Returns:
            List of matching products
        """
        pass

    @abstractmethod
    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """
        Get a specific product by its external ID.

        Args:
            external_id: The shop's product ID

        Returns:
            Product details or None if not found
        """
        pass

    @abstractmethod
    async def import_feed(self) -> list[ProductResult]:
        """
        Import the full product feed from the shop.

        Returns:
            List of all products from the feed
        """
        pass

    async def check_availability(self, external_id: str) -> tuple[bool, Optional[Decimal]]:
        """
        Check if a product is in stock and get current price.

        Args:
            external_id: The shop's product ID

        Returns:
            Tuple of (in_stock, current_price)
        """
        product = await self.get_product(external_id)
        if product:
            return product.in_stock, product.price
        return False, None

    def generate_affiliate_url(self, product_url: str) -> Optional[str]:
        """Generate affiliate URL for a product."""
        if not self.config.affiliate_url_template:
            return None

        return self.config.affiliate_url_template.format(
            url=product_url,
            affiliate_id=self.config.affiliate_id or "",
        )

    def calculate_relevance(self, product: ProductResult, query: SearchQuery) -> float:
        """
        Calculate relevance score for a product against a query.

        Scoring weights:
        - Brand match: 0.35 (critical for fashion)
        - Category/type match: 0.25
        - Query term matching: 0.20
        - Color match: 0.10
        - Style tags match: 0.05
        - Size availability: 0.05
        """
        score = 0.0

        # Normalize query terms
        query_lower = query.query.lower()
        query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 1]

        # Build searchable product text
        product_name_lower = (product.name or "").lower()
        product_brand_lower = (product.brand or "").lower()
        product_desc_lower = (product.description or "").lower()
        product_category_lower = (product.category or "").lower()
        product_color_lower = (product.color or "").lower()

        product_text = f"{product_name_lower} {product_brand_lower} {product_desc_lower} {product_category_lower}"

        # 1. Brand matching (0.35 max)
        brand_score = 0.0
        if query.brand:
            query_brand_lower = query.brand.lower()
            if product_brand_lower:
                if query_brand_lower == product_brand_lower:
                    brand_score = 0.35  # Exact match
                elif query_brand_lower in product_brand_lower or product_brand_lower in query_brand_lower:
                    brand_score = 0.25  # Partial match
        else:
            # Check if any query term matches brand
            for term in query_terms:
                if term in product_brand_lower:
                    brand_score = max(brand_score, 0.30)
                elif product_brand_lower and term in product_text:
                    brand_score = max(brand_score, 0.10)
        score += brand_score

        # 2. Category/type matching (0.25 max)
        category_score = 0.0
        category_synonyms = {
            "hoodie": ["hoodie", "hooded", "pullover", "sweatshirt"],
            "jacket": ["jacket", "coat", "blazer", "parka", "bomber"],
            "pants": ["pants", "trousers", "jeans", "chinos"],
            "shirt": ["shirt", "blouse", "top", "tee", "t-shirt"],
            "shoes": ["shoes", "sneakers", "boots", "trainers", "footwear"],
            "sweater": ["sweater", "jumper", "knit", "cardigan", "pullover"],
            "dress": ["dress", "gown"],
            "skirt": ["skirt"],
            "shorts": ["shorts"],
        }

        if query.category:
            query_cat = query.category.lower()
            synonyms = category_synonyms.get(query_cat, [query_cat])
            if any(syn in product_name_lower or syn in product_category_lower for syn in synonyms):
                category_score = 0.25
        else:
            # Check query terms for category matches
            for term in query_terms:
                synonyms = category_synonyms.get(term, [term])
                if any(syn in product_name_lower or syn in product_category_lower for syn in synonyms):
                    category_score = max(category_score, 0.20)
        score += category_score

        # 3. Query term matching (0.20 max)
        if query_terms:
            matched_terms = sum(1 for term in query_terms if term in product_text)
            term_score = (matched_terms / len(query_terms)) * 0.20
            score += term_score

        # 4. Color matching (0.10 max)
        color_score = 0.0
        color_synonyms = {
            "black": ["black", "noir", "svart"],
            "white": ["white", "cream", "ivory", "vit"],
            "blue": ["blue", "navy", "cobalt", "blå"],
            "red": ["red", "crimson", "röd"],
            "green": ["green", "olive", "grön"],
            "gray": ["gray", "grey", "charcoal", "grå"],
            "brown": ["brown", "tan", "camel", "brun"],
            "pink": ["pink", "rose", "rosa"],
            "beige": ["beige", "sand", "khaki"],
        }

        if query.color:
            query_color = query.color.lower()
            synonyms = color_synonyms.get(query_color, [query_color])
            if any(syn in product_color_lower or syn in product_name_lower for syn in synonyms):
                color_score = 0.10
        else:
            # Check query terms for color matches
            for term in query_terms:
                if term in product_color_lower:
                    color_score = max(color_score, 0.08)
        score += color_score

        # 5. Style tags matching (0.05 max)
        if query.style_tags:
            matching_tags = sum(1 for tag in query.style_tags if tag.lower() in product_text)
            if query.style_tags:
                score += (matching_tags / len(query.style_tags)) * 0.05

        # 6. Size availability (0.05 max)
        if query.size and product.sizes:
            if query.size.upper() in [s.upper() for s in product.sizes]:
                score += 0.05

        return min(score, 1.0)
