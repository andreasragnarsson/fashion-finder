"""Base Playwright scraper for JavaScript-rendered sites."""

import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from ..base import ProductResult, SearchQuery, ShopAdapter, ShopConfig


@dataclass
class ScraperConfig:
    """Configuration for Playwright scraper behavior."""

    headless: bool = True
    timeout: int = 30000  # milliseconds
    wait_for_selector: Optional[str] = None
    wait_for_timeout: int = 2000  # Additional wait after page load
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "sv-SE"


class PlaywrightScraper(ShopAdapter):
    """
    Base class for Playwright-based scrapers.

    Extend this class and implement the abstract methods for each shop.
    """

    def __init__(self, config: ShopConfig, scraper_config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.scraper_config = scraper_config or ScraperConfig()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _get_browser(self) -> Browser:
        """Get or create browser instance."""
        if self._browser is None or not self._browser.is_connected():
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=self.scraper_config.headless
            )
        return self._browser

    async def _get_context(self) -> BrowserContext:
        """Get or create browser context with proper settings."""
        browser = await self._get_browser()

        if self._context is None:
            self._context = await browser.new_context(
                user_agent=self.scraper_config.user_agent,
                viewport={
                    "width": self.scraper_config.viewport_width,
                    "height": self.scraper_config.viewport_height,
                },
                locale=self.scraper_config.locale,
            )
        return self._context

    async def _new_page(self) -> Page:
        """Create a new page with context settings."""
        context = await self._get_context()
        page = await context.new_page()
        page.set_default_timeout(self.scraper_config.timeout)
        return page

    async def _close(self):
        """Close browser resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None

    async def search(self, query: SearchQuery) -> List[ProductResult]:
        """Search for products using Playwright."""
        page = None
        try:
            page = await self._new_page()

            # Build and navigate to search URL
            search_url = self.build_search_url(query)
            await page.goto(search_url)

            # Wait for products to load
            await self._wait_for_products(page)

            # Handle cookie consent if present
            await self._handle_cookie_consent(page)

            # Extract products
            products = await self.extract_products(page, query)

            # Calculate relevance scores
            for product in products:
                product.relevance_score = self.calculate_relevance(product, query)

            # Sort by relevance and limit
            products.sort(key=lambda p: p.relevance_score, reverse=True)
            return products[:query.limit]

        except Exception as e:
            print(f"Playwright scraper error for {self.shop_id}: {e}")
            return []
        finally:
            if page:
                await page.close()

    async def _wait_for_products(self, page: Page):
        """Wait for products to load on page."""
        if self.scraper_config.wait_for_selector:
            try:
                await page.wait_for_selector(
                    self.scraper_config.wait_for_selector,
                    timeout=self.scraper_config.timeout
                )
            except Exception:
                pass  # Continue even if selector not found

        # Additional wait for JavaScript rendering
        await page.wait_for_timeout(self.scraper_config.wait_for_timeout)

    async def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent popups. Override in subclass if needed."""
        # Common cookie consent selectors
        consent_selectors = [
            'button:has-text("Acceptera")',
            'button:has-text("Accept")',
            'button:has-text("Godkänn")',
            '[data-testid="cookie-accept"]',
            '#onetrust-accept-btn-handler',
        ]

        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click()
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                continue

    @abstractmethod
    def build_search_url(self, query: SearchQuery) -> str:
        """
        Build the search URL for this shop.

        Args:
            query: Search query parameters

        Returns:
            Full URL to search results page
        """
        pass

    @abstractmethod
    async def extract_products(self, page: Page, query: SearchQuery) -> List[ProductResult]:
        """
        Extract products from the search results page.

        Args:
            page: Playwright page with search results
            query: Original search query

        Returns:
            List of ProductResult objects
        """
        pass

    async def get_product(self, external_id: str) -> Optional[ProductResult]:
        """Get a specific product by ID. Override if needed."""
        return None

    async def import_feed(self) -> List[ProductResult]:
        """Feed import not applicable for scrapers."""
        return []

    # Helper methods for subclasses

    def make_absolute_url(self, url: str, base_url: Optional[str] = None) -> str:
        """Convert relative URL to absolute."""
        if url.startswith(('http://', 'https://')):
            return url
        base = base_url or self.config.url
        return urljoin(base, url)

    def parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price from text, handling Swedish format."""
        if not price_text:
            return None

        import re

        # Remove currency symbols and text
        cleaned = re.sub(r'[^\d,.\s]', '', price_text)
        cleaned = cleaned.strip()

        if not cleaned:
            return None

        # Handle Swedish format: 1 234,56 or 1234,56
        cleaned = cleaned.replace(' ', '')  # Remove thousand separator

        # Replace comma with dot for decimal
        if ',' in cleaned:
            cleaned = cleaned.replace(',', '.')

        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def extract_sizes_from_text(self, text: str) -> List[str]:
        """Extract sizes from text."""
        import re

        # Common size patterns
        patterns = [
            r'\b(XXS|XS|S|M|L|XL|XXL|XXXL)\b',
            r'\b(\d{2,3})\b',  # Numeric sizes like 128, 140, 36, 38
            r'\b(\d{1,2}Y)\b',  # Kids ages like 8Y, 10Y
        ]

        sizes = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            sizes.extend(matches)

        return list(dict.fromkeys(sizes))  # Remove duplicates, preserve order
