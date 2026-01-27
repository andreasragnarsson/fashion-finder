"""Cost calculator for total cost including shipping, customs, and VAT."""

import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import httpx

from src.shops.base import ProductResult, ShopConfig, ShopRegion


# Default exchange rates (fallback)
DEFAULT_EXCHANGE_RATES = {
    "EUR": Decimal("11.50"),  # EUR to SEK
    "USD": Decimal("10.50"),  # USD to SEK
    "GBP": Decimal("13.50"),  # GBP to SEK
    "SEK": Decimal("1.0"),
}

# Swedish VAT rate
SWEDISH_VAT_RATE = Decimal("0.25")  # 25%

# EU customs threshold (value in EUR below which no customs apply)
# For non-EU imports to Sweden
CUSTOMS_THRESHOLD_EUR = Decimal("150")

# Customs duty rates by category (approximate)
CUSTOMS_RATES = {
    "clothing": Decimal("0.12"),  # 12%
    "footwear": Decimal("0.08"),  # 8%
    "accessories": Decimal("0.04"),  # 4%
    "default": Decimal("0.05"),  # 5%
}


class CostCalculator:
    """Calculate total cost including shipping, customs, and VAT for Swedish customers."""

    def __init__(self, exchange_rate_api_key: Optional[str] = None):
        self.api_key = exchange_rate_api_key or os.getenv("EXCHANGE_RATE_API_KEY")
        self._cached_rates: dict[str, Decimal] = {}

    async def get_exchange_rate(self, from_currency: str, to_currency: str = "SEK") -> Decimal:
        """
        Get exchange rate from one currency to another.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code (default SEK)

        Returns:
            Exchange rate as Decimal
        """
        if from_currency == to_currency:
            return Decimal("1.0")

        cache_key = f"{from_currency}_{to_currency}"
        if cache_key in self._cached_rates:
            return self._cached_rates[cache_key]

        # Try to fetch live rates
        if self.api_key:
            try:
                rate = await self._fetch_live_rate(from_currency, to_currency)
                self._cached_rates[cache_key] = rate
                return rate
            except Exception:
                pass

        # Fall back to default rates
        if to_currency == "SEK" and from_currency in DEFAULT_EXCHANGE_RATES:
            return DEFAULT_EXCHANGE_RATES[from_currency]

        # For non-SEK targets, calculate via SEK
        if to_currency != "SEK":
            from_to_sek = DEFAULT_EXCHANGE_RATES.get(from_currency, Decimal("1.0"))
            to_to_sek = DEFAULT_EXCHANGE_RATES.get(to_currency, Decimal("1.0"))
            return from_to_sek / to_to_sek

        return Decimal("1.0")

    async def _fetch_live_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Fetch live exchange rate from API."""
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        rate = data["rates"].get(to_currency)
        if rate is None:
            raise ValueError(f"Rate not found for {to_currency}")

        return Decimal(str(rate))

    def convert_to_sek(self, amount: Decimal, from_currency: str, rate: Decimal) -> Decimal:
        """Convert an amount to SEK."""
        if from_currency == "SEK":
            return amount
        return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_shipping(
        self,
        price: Decimal,
        config: ShopConfig,
    ) -> Decimal:
        """
        Calculate shipping cost based on shop configuration.

        Args:
            price: Product price in shop's currency
            config: Shop configuration

        Returns:
            Shipping cost in shop's currency
        """
        if not config.ships_to_sweden:
            return Decimal("0")  # Can't ship

        # Check free shipping threshold
        if config.free_shipping_threshold and price >= config.free_shipping_threshold:
            return Decimal("0")

        return config.base_shipping_cost or Decimal("0")

    def calculate_customs(
        self,
        price_eur: Decimal,
        shipping_eur: Decimal,
        region: ShopRegion,
        category: Optional[str] = None,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate customs duty and import VAT for non-EU purchases.

        For EU purchases (including Sweden), no customs apply.

        Args:
            price_eur: Product price in EUR
            shipping_eur: Shipping cost in EUR
            region: Shop's region
            category: Product category for duty rate

        Returns:
            Tuple of (customs_duty_eur, import_vat_eur)
        """
        # No customs within EU
        if region in (ShopRegion.SE, ShopRegion.EU):
            return Decimal("0"), Decimal("0")

        # Total value for customs assessment
        total_value = price_eur + shipping_eur

        # Below threshold - no customs, but VAT still applies
        if total_value <= CUSTOMS_THRESHOLD_EUR:
            customs_duty = Decimal("0")
        else:
            # Determine customs rate
            rate = CUSTOMS_RATES.get("default")
            if category:
                cat_lower = category.lower()
                if any(c in cat_lower for c in ["shirt", "pants", "jacket", "dress", "coat"]):
                    rate = CUSTOMS_RATES["clothing"]
                elif any(c in cat_lower for c in ["shoe", "boot", "sneaker", "sandal"]):
                    rate = CUSTOMS_RATES["footwear"]
                elif any(c in cat_lower for c in ["bag", "belt", "watch", "jewelry"]):
                    rate = CUSTOMS_RATES["accessories"]

            customs_duty = (price_eur * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Import VAT is calculated on (price + shipping + customs duty)
        vat_base = total_value + customs_duty
        import_vat = (vat_base * SWEDISH_VAT_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return customs_duty, import_vat

    async def calculate_total_cost(
        self,
        product: ProductResult,
        config: ShopConfig,
    ) -> ProductResult:
        """
        Calculate the total cost for a product including all fees.

        Args:
            product: The product to calculate costs for
            config: Shop configuration

        Returns:
            Product with cost fields populated
        """
        # Get exchange rate
        rate = await self.get_exchange_rate(product.currency)

        # Calculate shipping in original currency
        shipping = self.calculate_shipping(product.price, config)

        # Convert to EUR for customs calculation
        if product.currency == "EUR":
            price_eur = product.price
            shipping_eur = shipping
        else:
            eur_rate = await self.get_exchange_rate(product.currency, "EUR")
            price_eur = product.price * eur_rate
            shipping_eur = shipping * eur_rate

        # Calculate customs (only for non-EU)
        customs_eur, vat_eur = self.calculate_customs(
            price_eur, shipping_eur, config.region, product.category
        )

        # Convert customs costs to original currency, then to SEK
        if product.currency == "EUR":
            customs = customs_eur
            vat = vat_eur
        else:
            sek_to_eur = await self.get_exchange_rate("SEK", "EUR")
            eur_to_orig = await self.get_exchange_rate("EUR", product.currency)
            customs = customs_eur * eur_to_orig
            vat = vat_eur * eur_to_orig

        # Calculate total in original currency
        total = product.price + shipping + customs + vat

        # Convert to SEK
        total_sek = self.convert_to_sek(total, product.currency, rate)

        # Update product with costs
        product.shipping_cost = shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product.customs_cost = customs.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product.vat_cost = vat.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product.total_cost = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product.total_cost_sek = total_sek

        return product


# Singleton instance
_calculator: Optional[CostCalculator] = None


def get_cost_calculator() -> CostCalculator:
    """Get or create the cost calculator singleton."""
    global _calculator
    if _calculator is None:
        _calculator = CostCalculator()
    return _calculator


async def calculate_total_cost(product: ProductResult, config: ShopConfig) -> ProductResult:
    """Convenience function to calculate total cost for a product."""
    calculator = get_cost_calculator()
    return await calculator.calculate_total_cost(product, config)
