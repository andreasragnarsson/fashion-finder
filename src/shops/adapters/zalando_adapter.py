"""Zalando.se scraper adapter."""

import re
from decimal import Decimal
from typing import Optional, List
from urllib.parse import urlencode, quote_plus

import httpx
from bs4 import BeautifulSoup

from ..base import ProductResult, SearchQuery, ShopAdapter, ShopConfig


class ZalandoAdapter(ShopAdapter):
    """Adapter for Zalando.se using their website search."""

    def __init__(self, config: ShopConfig):
        super().__init__(config)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
        }

    async def search(self, query: SearchQuery) -> List[ProductResult]:
        """Search Zalando.se for products."""
        # Build search URL
        search_url = self._build_search_url(query)

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers=self._headers)
                response.raise_for_status()

            products = self._parse_search_results(response.text, query)
            return products[:query.limit]

        except Exception as e:
            print(f"Zalando search error: {e}")
            return []

    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """Get a specific product - not implemented for scraper."""
        return None

    async def import_feed(self) -> List[ProductResult]:
        """Feed import not supported for scraper."""
        return []

    def _build_search_url(self, query: SearchQuery) -> str:
        """Build Zalando search URL."""
        base_url = "https://www.zalando.se/damklader/"  # Default to women's

        # Adjust category based on gender
        if query.gender:
            gender_lower = query.gender.lower()
            if gender_lower in ['men', 'man', 'herr']:
                base_url = "https://www.zalando.se/herrklader/"
            elif gender_lower in ['kids', 'barn', 'children']:
                base_url = "https://www.zalando.se/barnklader/"

        # Build query params
        params = {
            'q': query.query,
        }

        return f"{base_url}?{urlencode(params)}"

    def _parse_search_results(self, html: str, query: SearchQuery) -> List[ProductResult]:
        """Parse Zalando search results page."""
        soup = BeautifulSoup(html, 'lxml')
        products = []

        # Find product articles - Zalando uses article tags with specific data attributes
        # Try multiple selectors as Zalando's HTML structure can vary
        articles = soup.select('article[class*="product"]') or \
                   soup.select('div[class*="catalog"] article') or \
                   soup.select('[data-testid*="product"]')

        if not articles:
            # Try finding product links directly
            articles = soup.select('a[href*="/p/"]')

        for article in articles[:query.limit * 2]:  # Get extra to filter
            try:
                product = self._parse_product_article(article, query)
                if product:
                    products.append(product)
            except Exception as e:
                continue

        # Sort by relevance
        products.sort(key=lambda p: p.relevance_score, reverse=True)
        return products

    def _parse_product_article(self, article, query: SearchQuery) -> Optional[ProductResult]:
        """Parse a single product article."""
        # Try to find product link
        link = article.get('href') if article.name == 'a' else None
        if not link:
            link_elem = article.select_one('a[href*="/p/"]') or article.select_one('a[href]')
            link = link_elem.get('href') if link_elem else None

        if not link:
            return None

        # Make absolute URL
        if link.startswith('/'):
            link = f"https://www.zalando.se{link}"

        # Extract product ID from URL
        external_id = self._extract_product_id(link)
        if not external_id:
            return None

        # Find product name
        name = None
        name_selectors = [
            '[class*="name"]', '[class*="title"]', 'h3', 'h2',
            '[data-testid*="name"]', '[data-testid*="title"]'
        ]
        for selector in name_selectors:
            name_elem = article.select_one(selector)
            if name_elem and name_elem.get_text(strip=True):
                name = name_elem.get_text(strip=True)
                break

        if not name:
            # Try getting text from the article itself
            name = article.get_text(strip=True)[:100]

        if not name:
            return None

        # Find brand
        brand = None
        brand_selectors = ['[class*="brand"]', '[data-testid*="brand"]']
        for selector in brand_selectors:
            brand_elem = article.select_one(selector)
            if brand_elem:
                brand = brand_elem.get_text(strip=True)
                break

        # Find price
        price = None
        price_selectors = [
            '[class*="price"]', '[data-testid*="price"]',
            'span[class*="amount"]', 'p[class*="price"]'
        ]
        for selector in price_selectors:
            price_elems = article.select(selector)
            for price_elem in price_elems:
                price_text = price_elem.get_text(strip=True)
                parsed_price = self._parse_price(price_text)
                if parsed_price:
                    price = parsed_price
                    break
            if price:
                break

        if not price:
            price = Decimal("0")

        # Find image
        image_url = None
        img = article.select_one('img[src]') or article.select_one('img[data-src]')
        if img:
            image_url = img.get('src') or img.get('data-src')
            if image_url and image_url.startswith('//'):
                image_url = f"https:{image_url}"

        product = ProductResult(
            shop_id=self.shop_id,
            external_id=external_id,
            name=name,
            brand=brand,
            price=price,
            currency="SEK",
            product_url=link,
            image_url=image_url,
            in_stock=True,
        )

        product.relevance_score = self.calculate_relevance(product, query)
        return product

    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Zalando URL."""
        # Zalando URLs look like: /product-name.html or /brand-product.AB123CD456.html
        match = re.search(r'\.([A-Z0-9]{10,})\.(html)?', url)
        if match:
            return match.group(1)

        # Try to get last path segment
        parts = url.rstrip('/').split('/')
        if parts:
            last = parts[-1].replace('.html', '')
            if last:
                return last

        return None

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price from text."""
        if not price_text:
            return None

        # Remove common currency symbols and text
        cleaned = re.sub(r'[^\d,.\s]', '', price_text)
        cleaned = cleaned.strip()

        if not cleaned:
            return None

        # Handle Swedish format: 1 234,56 or 1234,56
        # Remove spaces (thousand separator)
        cleaned = cleaned.replace(' ', '')

        # Replace comma with dot for decimal
        if ',' in cleaned:
            cleaned = cleaned.replace(',', '.')

        try:
            return Decimal(cleaned)
        except:
            return None
