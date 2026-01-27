"""Kidsbrandstore.se adapter with sample products for MVP testing."""

from decimal import Decimal
from typing import Optional, List

from ..base import ProductResult, SearchQuery, ShopAdapter, ShopConfig


# Sample products from Kidsbrandstore for MVP testing
SAMPLE_PRODUCTS = [
    {
        "id": "nike-air-force-1-white",
        "name": "Nike Air Force 1 Low White",
        "brand": "Nike",
        "price": Decimal("1099"),
        "category": "shoes",
        "color": "white",
        "sizes": ["28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38"],
        "url": "https://www.kidsbrandstore.se/sv/p/nike-air-force-1-low-white",
        "image": "https://www.kidsbrandstore.se/images/nike-air-force-1-white.jpg",
        "keywords": ["nike", "air force", "sneakers", "white", "skor"],
    },
    {
        "id": "nike-tech-fleece-hoodie-black",
        "name": "Nike Sportswear Tech Fleece Hoodie Black",
        "brand": "Nike",
        "price": Decimal("899"),
        "category": "hoodie",
        "color": "black",
        "sizes": ["128", "140", "152", "164", "176"],
        "url": "https://www.kidsbrandstore.se/sv/p/nike-tech-fleece-hoodie-black",
        "image": "https://www.kidsbrandstore.se/images/nike-tech-fleece-black.jpg",
        "keywords": ["nike", "tech fleece", "hoodie", "black", "svart", "tröja"],
    },
    {
        "id": "nike-dunk-low-panda",
        "name": "Nike Dunk Low Retro White Black (Panda)",
        "brand": "Nike",
        "price": Decimal("1199"),
        "category": "shoes",
        "color": "white/black",
        "sizes": ["36", "37", "38", "39", "40"],
        "url": "https://www.kidsbrandstore.se/sv/p/nike-dunk-low-panda",
        "image": "https://www.kidsbrandstore.se/images/nike-dunk-panda.jpg",
        "keywords": ["nike", "dunk", "panda", "sneakers", "skor"],
    },
    {
        "id": "adidas-superstar-white",
        "name": "Adidas Originals Superstar White",
        "brand": "Adidas",
        "price": Decimal("899"),
        "category": "shoes",
        "color": "white",
        "sizes": ["28", "29", "30", "31", "32", "33", "34", "35"],
        "url": "https://www.kidsbrandstore.se/sv/p/adidas-superstar-white",
        "image": "https://www.kidsbrandstore.se/images/adidas-superstar.jpg",
        "keywords": ["adidas", "superstar", "originals", "sneakers", "white", "vit"],
    },
    {
        "id": "adidas-trefoil-hoodie-navy",
        "name": "Adidas Originals Trefoil Hoodie Navy",
        "brand": "Adidas",
        "price": Decimal("549"),
        "category": "hoodie",
        "color": "navy",
        "sizes": ["128", "140", "152", "164"],
        "url": "https://www.kidsbrandstore.se/sv/p/adidas-trefoil-hoodie-navy",
        "image": "https://www.kidsbrandstore.se/images/adidas-trefoil-navy.jpg",
        "keywords": ["adidas", "trefoil", "hoodie", "navy", "blå", "tröja"],
    },
    {
        "id": "moncler-maya-jacket-black",
        "name": "Moncler Maya Down Jacket Black",
        "brand": "Moncler",
        "price": Decimal("8500"),
        "original_price": Decimal("9500"),
        "category": "jacket",
        "color": "black",
        "sizes": ["8Y", "10Y", "12Y", "14Y"],
        "url": "https://www.kidsbrandstore.se/sv/p/moncler-maya-jacket-black",
        "image": "https://www.kidsbrandstore.se/images/moncler-maya.jpg",
        "keywords": ["moncler", "maya", "down jacket", "dunjacka", "black", "luxury"],
    },
    {
        "id": "ralph-lauren-polo-navy",
        "name": "Ralph Lauren Classic Polo Shirt Navy",
        "brand": "Ralph Lauren",
        "price": Decimal("699"),
        "category": "shirt",
        "color": "navy",
        "sizes": ["S", "M", "L", "XL"],
        "url": "https://www.kidsbrandstore.se/sv/p/ralph-lauren-polo-navy",
        "image": "https://www.kidsbrandstore.se/images/ralph-polo-navy.jpg",
        "keywords": ["ralph lauren", "polo", "shirt", "navy", "classic"],
    },
    {
        "id": "north-face-nuptse-black",
        "name": "The North Face 1996 Retro Nuptse Jacket Black",
        "brand": "The North Face",
        "price": Decimal("2799"),
        "category": "jacket",
        "color": "black",
        "sizes": ["XS", "S", "M", "L"],
        "url": "https://www.kidsbrandstore.se/sv/p/north-face-nuptse-black",
        "image": "https://www.kidsbrandstore.se/images/tnf-nuptse.jpg",
        "keywords": ["north face", "nuptse", "1996", "puffer", "jacket", "dunjacka"],
    },
    {
        "id": "burberry-check-shirt",
        "name": "Burberry Vintage Check Cotton Shirt",
        "brand": "Burberry",
        "price": Decimal("3200"),
        "category": "shirt",
        "color": "beige",
        "sizes": ["6Y", "8Y", "10Y", "12Y"],
        "url": "https://www.kidsbrandstore.se/sv/p/burberry-check-shirt",
        "image": "https://www.kidsbrandstore.se/images/burberry-check.jpg",
        "keywords": ["burberry", "check", "vintage", "shirt", "skjorta", "luxury"],
    },
    {
        "id": "gucci-ace-sneakers",
        "name": "Gucci Ace Leather Sneakers White",
        "brand": "Gucci",
        "price": Decimal("4500"),
        "category": "shoes",
        "color": "white",
        "sizes": ["30", "31", "32", "33", "34"],
        "url": "https://www.kidsbrandstore.se/sv/p/gucci-ace-sneakers",
        "image": "https://www.kidsbrandstore.se/images/gucci-ace.jpg",
        "keywords": ["gucci", "ace", "sneakers", "leather", "white", "luxury"],
    },
    {
        "id": "jordan-1-retro-chicago",
        "name": "Air Jordan 1 Retro High OG Chicago",
        "brand": "Jordan",
        "price": Decimal("1899"),
        "category": "shoes",
        "color": "red/white/black",
        "sizes": ["36", "37", "38", "39", "40"],
        "url": "https://www.kidsbrandstore.se/sv/p/jordan-1-chicago",
        "image": "https://www.kidsbrandstore.se/images/jordan1-chicago.jpg",
        "keywords": ["jordan", "air jordan", "retro", "chicago", "sneakers", "nike"],
    },
    {
        "id": "levis-501-jeans",
        "name": "Levi's 501 Original Fit Jeans Blue",
        "brand": "Levi's",
        "price": Decimal("799"),
        "category": "jeans",
        "color": "blue",
        "sizes": ["128", "140", "152", "164", "176"],
        "url": "https://www.kidsbrandstore.se/sv/p/levis-501-jeans",
        "image": "https://www.kidsbrandstore.se/images/levis-501.jpg",
        "keywords": ["levis", "501", "jeans", "denim", "blue", "original"],
    },
]


class KidsbrandstoreAdapter(ShopAdapter):
    """Adapter for Kidsbrandstore.se with sample products for MVP."""

    def __init__(self, config: ShopConfig):
        super().__init__(config)
        self._products = {p["id"]: p for p in SAMPLE_PRODUCTS}

    async def search(self, query: SearchQuery) -> List[ProductResult]:
        """Search sample products."""
        results = []
        query_lower = query.query.lower()
        query_terms = query_lower.split()

        for product_data in SAMPLE_PRODUCTS:
            # Build searchable text
            searchable = " ".join([
                product_data["name"].lower(),
                product_data["brand"].lower(),
                product_data.get("category", "").lower(),
                product_data.get("color", "").lower(),
                " ".join(product_data.get("keywords", [])).lower(),
            ])

            # Check if any query term matches
            if any(term in searchable for term in query_terms):
                product = self._to_product_result(product_data)
                product.relevance_score = self._calculate_relevance(product_data, query_terms, searchable)
                results.append(product)

        # Sort by relevance
        results.sort(key=lambda p: p.relevance_score, reverse=True)
        return results[:query.limit]

    def _calculate_relevance(self, product_data: dict, query_terms: list, searchable: str) -> float:
        """Calculate relevance score."""
        score = 0.0

        # Brand match (high weight)
        brand_lower = product_data["brand"].lower()
        for term in query_terms:
            if term in brand_lower:
                score += 0.4

        # Exact name match
        name_lower = product_data["name"].lower()
        for term in query_terms:
            if term in name_lower:
                score += 0.3

        # Keyword match
        keywords = " ".join(product_data.get("keywords", [])).lower()
        for term in query_terms:
            if term in keywords:
                score += 0.2

        # Category match
        if any(term in product_data.get("category", "").lower() for term in query_terms):
            score += 0.1

        return min(score, 1.0)

    def _to_product_result(self, data: dict) -> ProductResult:
        """Convert sample data to ProductResult."""
        return ProductResult(
            shop_id=self.shop_id,
            external_id=data["id"],
            name=data["name"],
            brand=data["brand"],
            price=data["price"],
            original_price=data.get("original_price"),
            currency="SEK",
            category=data.get("category"),
            color=data.get("color"),
            sizes=data.get("sizes", []),
            product_url=data["url"],
            image_url=data.get("image"),
            in_stock=True,
            gender="kids",
        )

    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """Get a specific product by ID."""
        data = self._products.get(external_id)
        if data:
            return self._to_product_result(data)
        return None

    async def import_feed(self) -> List[ProductResult]:
        """Return all sample products."""
        return [self._to_product_result(p) for p in SAMPLE_PRODUCTS]
