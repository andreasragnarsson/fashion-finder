"""Generic adapter for affiliate product feeds (CSV/XML)."""

import csv
import io
from decimal import Decimal
from typing import Optional
from xml.etree import ElementTree

import httpx
from aiolimiter import AsyncLimiter

from ..base import ProductResult, SearchQuery, ShopAdapter, ShopConfig


class FeedAdapter(ShopAdapter):
    """Adapter for shops that provide product feeds."""

    def __init__(self, config: ShopConfig):
        super().__init__(config)
        self._products: dict[str, ProductResult] = {}
        self._last_import: Optional[float] = None
        self._rate_limiter = AsyncLimiter(30, 60)  # 30 requests per minute

    async def search(self, query: SearchQuery) -> list[ProductResult]:
        """Search loaded products for matches."""
        if not self._products:
            await self.import_feed()

        results = []
        query_lower = query.query.lower()
        query_terms = query_lower.split()

        for product in self._products.values():
            # Check basic filters
            if query.gender and product.gender:
                if query.gender.lower() != product.gender.lower():
                    continue

            if query.category and product.category:
                if query.category.lower() not in product.category.lower():
                    continue

            if query.brand and product.brand:
                if query.brand.lower() not in product.brand.lower():
                    continue

            if query.color and product.color:
                if query.color.lower() not in product.color.lower():
                    continue

            if query.min_price and product.price < query.min_price:
                continue

            if query.max_price and product.price > query.max_price:
                continue

            if query.size and product.sizes:
                if query.size.upper() not in [s.upper() for s in product.sizes]:
                    continue

            # Text search
            search_text = f"{product.name} {product.brand or ''} {product.description or ''} {product.category or ''}".lower()
            if not any(term in search_text for term in query_terms):
                continue

            # Calculate relevance
            product.relevance_score = self.calculate_relevance(product, query)
            results.append(product)

        # Sort by relevance and limit
        results.sort(key=lambda p: p.relevance_score, reverse=True)
        return results[: query.limit]

    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """Get a product by external ID."""
        if not self._products:
            await self.import_feed()

        return self._products.get(external_id)

    async def import_feed(self) -> list[ProductResult]:
        """Import products from the feed URL."""
        if not self.config.feed_url:
            return []

        async with self._rate_limiter:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.config.feed_url)
                response.raise_for_status()
                content = response.text

        # Parse based on feed type
        if self.config.feed_type == "xml":
            products = self._parse_xml_feed(content)
        else:
            products = self._parse_csv_feed(content)

        # Store in memory
        self._products = {p.external_id: p for p in products}

        return products

    def _parse_csv_feed(self, content: str) -> list[ProductResult]:
        """Parse a CSV product feed."""
        products = []
        mapping = self.config.feed_mapping

        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            try:
                product = self._map_row_to_product(row, mapping)
                if product:
                    products.append(product)
            except Exception as e:
                # Skip malformed rows
                continue

        return products

    def _parse_xml_feed(self, content: str) -> list[ProductResult]:
        """Parse an XML product feed."""
        products = []
        mapping = self.config.feed_mapping

        root = ElementTree.fromstring(content)

        # Handle common XML feed formats
        item_tag = mapping.get("item_tag", "item")
        for item in root.iter(item_tag):
            try:
                row = {child.tag: child.text for child in item}
                product = self._map_row_to_product(row, mapping)
                if product:
                    products.append(product)
            except Exception:
                continue

        return products

    def _map_row_to_product(self, row: dict, mapping: dict) -> Optional[ProductResult]:
        """Map a feed row to a ProductResult using the column mapping."""
        # Get required fields
        external_id = row.get(mapping.get("id", "id"))
        name = row.get(mapping.get("name", "name"))
        price_str = row.get(mapping.get("price", "price"))

        if not all([external_id, name, price_str]):
            return None

        # Parse price
        try:
            price = Decimal(str(price_str).replace(",", ".").strip())
        except:
            return None

        # Parse optional price
        original_price = None
        orig_price_str = row.get(mapping.get("original_price", "original_price"))
        if orig_price_str:
            try:
                original_price = Decimal(str(orig_price_str).replace(",", ".").strip())
            except:
                pass

        # Parse sizes
        sizes = []
        sizes_str = row.get(mapping.get("sizes", "sizes"), "")
        if sizes_str:
            sizes = [s.strip() for s in str(sizes_str).split(",")]

        # Generate affiliate URL
        product_url = row.get(mapping.get("url", "url"), "")
        affiliate_url = self.generate_affiliate_url(product_url)

        return ProductResult(
            shop_id=self.shop_id,
            external_id=str(external_id),
            name=str(name),
            brand=row.get(mapping.get("brand", "brand")),
            price=price,
            currency=self.config.currency,
            original_price=original_price,
            category=row.get(mapping.get("category", "category")),
            color=row.get(mapping.get("color", "color")),
            sizes=sizes,
            material=row.get(mapping.get("material", "material")),
            gender=row.get(mapping.get("gender", "gender")),
            description=row.get(mapping.get("description", "description")),
            product_url=product_url,
            affiliate_url=affiliate_url,
            image_url=row.get(mapping.get("image_url", "image_url")),
            in_stock=row.get(mapping.get("in_stock", "in_stock"), "true").lower() == "true",
        )
