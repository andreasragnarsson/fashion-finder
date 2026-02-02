"""Kidsbrandstore.se Playwright scraper."""

import re
from decimal import Decimal
from typing import Optional, List
from urllib.parse import urlencode

from playwright.async_api import Page

from ..base import ProductResult, SearchQuery, ShopConfig
from .playwright_base import PlaywrightScraper, ScraperConfig


class KidsbrandstorePlaywright(PlaywrightScraper):
    """
    Playwright-based scraper for Kidsbrandstore.se.

    Kidsbrandstore uses Next.js with heavy JavaScript rendering,
    requiring browser automation for reliable scraping.
    """

    def __init__(self, config: ShopConfig):
        scraper_config = ScraperConfig(
            headless=True,
            timeout=30000,
            wait_for_selector='a[href*="/products/"]',
            wait_for_timeout=5000,  # Extra time for Next.js hydration
            locale="sv-SE",
        )
        super().__init__(config, scraper_config)

    def build_search_url(self, query: SearchQuery) -> str:
        """Build Kidsbrandstore search URL."""
        base_url = "https://www.kidsbrandstore.se/sv/search"
        params = {"q": query.query}
        return f"{base_url}?{urlencode(params)}"

    async def _handle_cookie_consent(self, page: Page):
        """Handle Kidsbrandstore cookie consent (Cookiebot)."""
        try:
            btn = page.locator('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    async def extract_products(self, page: Page, query: SearchQuery) -> List[ProductResult]:
        """Extract products from Kidsbrandstore search results."""
        products = []

        # Find product images with links to /products/
        product_images = page.locator('img[src*="kidsbrandstore.com"], img[src*="/_next/image"]')
        count = await product_images.count()

        for i in range(min(query.limit * 2, count)):
            try:
                img = product_images.nth(i)

                # Get parent link
                parent_link = img.locator('xpath=ancestor::a').first
                if await parent_link.count() == 0:
                    continue

                href = await parent_link.get_attribute('href')
                if not href or '/products/' not in href:
                    continue

                # Get product container (parent with class containing "group")
                container = img.locator('xpath=ancestor::*[contains(@class, "group")]').first

                product = await self._parse_product(
                    href=href,
                    img=img,
                    container=container if await container.count() > 0 else None
                )

                if product:
                    products.append(product)

            except Exception as e:
                continue

        return products

    async def _parse_product(
        self,
        href: str,
        img,
        container
    ) -> Optional[ProductResult]:
        """Parse product data from page elements."""
        try:
            # Get image URL
            src = await img.get_attribute('src')
            image_url = self._clean_image_url(src) if src else None

            # Get alt text (sometimes has product name)
            alt = await img.get_attribute('alt') or ""

            # Extract product ID from URL
            external_id = self._extract_product_id(href)
            product_url = self.make_absolute_url(href)

            # Default values
            name = alt or self._name_from_url(href)
            brand = None
            price = Decimal("0")

            # Try to get info from container text
            if container:
                text = await container.text_content()
                if text:
                    parsed = self._parse_container_text(text)
                    brand = parsed.get('brand')
                    name = parsed.get('name') or name
                    price = parsed.get('price') or price

            if not name:
                return None

            return ProductResult(
                shop_id=self.shop_id,
                external_id=external_id,
                name=name,
                brand=brand,
                price=price,
                currency="SEK",
                product_url=product_url,
                image_url=image_url,
                in_stock=True,
                gender="kids",
            )

        except Exception as e:
            return None

    def _parse_container_text(self, text: str) -> dict:
        """
        Parse container text to extract brand, name, price.

        Example text: "NyhetLyle & ScottCrew Neck Sweatshirt649 kr"
        """
        result = {}

        # Remove common prefixes
        text = text.replace('Nyhet', '').strip()

        # Extract price (digits followed by kr)
        price_match = re.search(r'(\d[\d\s]*)\s*kr', text)
        if price_match:
            price_str = price_match.group(1).replace(' ', '')
            try:
                result['price'] = Decimal(price_str)
            except:
                pass
            # Remove price from text
            text = text[:price_match.start()].strip()

        # Known brands to look for
        known_brands = [
            'Nike', 'Adidas', 'Adidas Originals', 'Adidas Performance',
            'Jordan', 'Puma', 'New Balance', 'Reebok', 'Converse', 'Vans',
            'Lyle & Scott', 'Ralph Lauren', 'Tommy Hilfiger', 'Calvin Klein',
            'The North Face', 'Moncler', 'Burberry', 'Gucci', 'Gant',
            'Peak Performance', 'Helly Hansen', 'Patagonia', 'Columbia',
            "Levi's", 'Lee', 'Diesel', 'Boss', 'Lacoste', 'Kenzo',
            'Stone Island', 'CP Company', 'Dsquared2', 'Moschino',
        ]

        for brand in known_brands:
            if brand in text:
                result['brand'] = brand
                # Extract name after brand
                idx = text.index(brand) + len(brand)
                name = text[idx:].strip()
                if name:
                    result['name'] = name
                break

        if 'name' not in result and text:
            result['name'] = text

        return result

    def _extract_product_id(self, url: str) -> str:
        """Extract product ID from URL like /products/crew-neck-sweatshirt-1308943."""
        match = re.search(r'/products/([^/?]+)', url)
        if match:
            return match.group(1)
        return url.split('/')[-1]

    def _name_from_url(self, url: str) -> str:
        """Generate product name from URL."""
        product_id = self._extract_product_id(url)
        # Remove trailing number ID
        name = re.sub(r'-\d+$', '', product_id)
        # Convert hyphens to spaces and title case
        return name.replace('-', ' ').title()

    def _clean_image_url(self, src: str) -> str:
        """Clean and decode image URL."""
        if '/_next/image' in src:
            # Extract original URL from Next.js image optimizer
            match = re.search(r'url=([^&]+)', src)
            if match:
                from urllib.parse import unquote
                return unquote(match.group(1))
        return src
