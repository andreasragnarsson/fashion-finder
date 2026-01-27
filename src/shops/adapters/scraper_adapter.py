"""Generic scraper adapter for shops without feeds."""

import re
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin, urlencode

import httpx
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup

from ..base import ProductResult, SearchQuery, ShopAdapter, ShopConfig


class ScraperAdapter(ShopAdapter):
    """Adapter for shops that require scraping."""

    def __init__(self, config: ShopConfig):
        super().__init__(config)
        # Respectful rate limiting: 1 request per 2 seconds
        self._rate_limiter = AsyncLimiter(1, 2)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FashionFinderBot/1.0; +https://fashionfinder.example.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
        }

    async def search(self, query: SearchQuery) -> list[ProductResult]:
        """Search the shop by scraping search results."""
        search_url = self._build_search_url(query)

        async with self._rate_limiter:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers=self._headers)
                response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        products = self._parse_search_results(soup, query)

        return products[: query.limit]

    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """Get product details by scraping the product page."""
        product_url = self._build_product_url(external_id)

        async with self._rate_limiter:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(product_url, headers=self._headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        return self._parse_product_page(soup, external_id, product_url)

    async def import_feed(self) -> list[ProductResult]:
        """Scraper adapters don't support full feed import."""
        return []

    def _build_search_url(self, query: SearchQuery) -> str:
        """Build the search URL for the shop."""
        # This should be customized per shop in config
        mapping = self.config.feed_mapping
        search_path = mapping.get("search_path", "/search")
        query_param = mapping.get("query_param", "q")

        params = {query_param: query.query}

        if query.category:
            category_param = mapping.get("category_param", "category")
            params[category_param] = query.category

        if query.gender:
            gender_param = mapping.get("gender_param", "gender")
            params[gender_param] = query.gender

        return f"{self.config.url.rstrip('/')}{search_path}?{urlencode(params)}"

    def _build_product_url(self, external_id: str) -> str:
        """Build the product URL from external ID."""
        mapping = self.config.feed_mapping
        product_path = mapping.get("product_path", "/product/{id}")
        return f"{self.config.url.rstrip('/')}{product_path.format(id=external_id)}"

    def _parse_search_results(self, soup: BeautifulSoup, query: SearchQuery) -> list[ProductResult]:
        """Parse search results page. Override per shop as needed."""
        mapping = self.config.feed_mapping
        products = []

        # Generic selectors - should be customized per shop
        item_selector = mapping.get("item_selector", ".product-item")
        name_selector = mapping.get("name_selector", ".product-name")
        price_selector = mapping.get("price_selector", ".product-price")
        image_selector = mapping.get("image_selector", "img")
        link_selector = mapping.get("link_selector", "a")

        for item in soup.select(item_selector):
            try:
                # Extract name
                name_elem = item.select_one(name_selector)
                name = name_elem.get_text(strip=True) if name_elem else None

                # Extract price
                price_elem = item.select_one(price_selector)
                price_text = price_elem.get_text(strip=True) if price_elem else None
                price = self._parse_price(price_text) if price_text else None

                # Extract image
                img_elem = item.select_one(image_selector)
                image_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else None
                if image_url and not image_url.startswith("http"):
                    image_url = urljoin(self.config.url, image_url)

                # Extract link
                link_elem = item.select_one(link_selector)
                product_url = link_elem.get("href") if link_elem else None
                if product_url and not product_url.startswith("http"):
                    product_url = urljoin(self.config.url, product_url)

                # Extract ID from URL
                external_id = self._extract_id_from_url(product_url) if product_url else None

                if not all([name, price, external_id]):
                    continue

                product = ProductResult(
                    shop_id=self.shop_id,
                    external_id=external_id,
                    name=name,
                    brand=self._extract_brand(item, mapping),
                    price=price,
                    currency=self.config.currency,
                    product_url=product_url or "",
                    affiliate_url=self.generate_affiliate_url(product_url) if product_url else None,
                    image_url=image_url,
                    in_stock=True,
                )
                product.relevance_score = self.calculate_relevance(product, query)
                products.append(product)

            except Exception:
                continue

        products.sort(key=lambda p: p.relevance_score, reverse=True)
        return products

    def _parse_product_page(
        self, soup: BeautifulSoup, external_id: str, product_url: str
    ) -> Optional[ProductResult]:
        """Parse a product detail page. Override per shop as needed."""
        mapping = self.config.feed_mapping

        # Generic selectors
        name_selector = mapping.get("detail_name_selector", "h1")
        price_selector = mapping.get("detail_price_selector", ".price")
        image_selector = mapping.get("detail_image_selector", ".product-image img")
        description_selector = mapping.get("detail_description_selector", ".product-description")

        name_elem = soup.select_one(name_selector)
        name = name_elem.get_text(strip=True) if name_elem else None

        price_elem = soup.select_one(price_selector)
        price_text = price_elem.get_text(strip=True) if price_elem else None
        price = self._parse_price(price_text) if price_text else None

        if not all([name, price]):
            return None

        img_elem = soup.select_one(image_selector)
        image_url = img_elem.get("src") if img_elem else None
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(self.config.url, image_url)

        desc_elem = soup.select_one(description_selector)
        description = desc_elem.get_text(strip=True) if desc_elem else None

        return ProductResult(
            shop_id=self.shop_id,
            external_id=external_id,
            name=name,
            brand=None,
            price=price,
            currency=self.config.currency,
            description=description,
            product_url=product_url,
            affiliate_url=self.generate_affiliate_url(product_url),
            image_url=image_url,
            in_stock=True,
        )

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Extract numeric price from text."""
        if not price_text:
            return None

        # Remove currency symbols and whitespace
        cleaned = re.sub(r"[^\d,.]", "", price_text)

        # Handle European format (1.234,56) vs US format (1,234.56)
        if "," in cleaned and "." in cleaned:
            if cleaned.index(",") > cleaned.index("."):
                # European format
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # US format
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Could be European decimal or US thousands separator
            if len(cleaned.split(",")[-1]) == 2:
                # Likely European decimal
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return Decimal(cleaned)
        except:
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract product ID from URL."""
        if not url:
            return None

        # Try common patterns
        patterns = [
            r"/product/(\d+)",
            r"/p/(\d+)",
            r"/(\d+)\.html",
            r"[?&]id=(\d+)",
            r"/([A-Z0-9]{6,})",  # SKU-like patterns
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Fall back to using last path segment
        from urllib.parse import urlparse

        path = urlparse(url).path
        segments = [s for s in path.split("/") if s]
        if segments:
            return segments[-1]

        return None

    def _extract_brand(self, item, mapping: dict) -> Optional[str]:
        """Extract brand from a product item."""
        brand_selector = mapping.get("brand_selector", ".brand")
        brand_elem = item.select_one(brand_selector)
        return brand_elem.get_text(strip=True) if brand_elem else None
