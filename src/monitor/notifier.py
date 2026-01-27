"""Email notification service using Resend."""

import os
from dataclasses import dataclass
from typing import Optional

import resend

from .price_checker import PriceCheck


@dataclass
class NotificationResult:
    """Result of sending a notification."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailNotifier:
    """Send email notifications via Resend."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        self.from_email = from_email or os.getenv("FROM_EMAIL", "alerts@fashionfinder.app")

        if self.api_key:
            resend.api_key = self.api_key

    def send_price_drop_alert(
        self,
        to_email: str,
        product_name: str,
        shop_name: str,
        old_price: float,
        new_price: float,
        currency: str,
        product_url: str,
        drop_percent: float,
    ) -> NotificationResult:
        """
        Send a price drop alert email.

        Args:
            to_email: Recipient email
            product_name: Name of the product
            shop_name: Shop where the product is sold
            old_price: Previous price
            new_price: New (lower) price
            currency: Price currency
            product_url: Link to the product
            drop_percent: Percentage drop

        Returns:
            NotificationResult with success status
        """
        if not self.api_key:
            return NotificationResult(
                success=False,
                error="Resend API key not configured",
            )

        subject = f"Price Drop Alert: {product_name} is now {drop_percent:.0f}% off!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4a90d9; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .price-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .old-price {{ color: #999; text-decoration: line-through; font-size: 18px; }}
                .new-price {{ color: #28a745; font-size: 24px; font-weight: bold; }}
                .drop-badge {{ background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; }}
                .cta-button {{
                    display: inline-block;
                    background: #4a90d9;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 15px;
                }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Price Drop Alert!</h1>
                </div>
                <div class="content">
                    <h2>{product_name}</h2>
                    <p>Great news! An item on your watchlist just got cheaper at <strong>{shop_name}</strong>.</p>

                    <div class="price-box">
                        <p><span class="old-price">{old_price:.2f} {currency}</span></p>
                        <p><span class="new-price">{new_price:.2f} {currency}</span></p>
                        <p><span class="drop-badge">-{drop_percent:.0f}%</span></p>
                    </div>

                    <p>You're saving <strong>{old_price - new_price:.2f} {currency}</strong>!</p>

                    <a href="{product_url}" class="cta-button">View Product</a>
                </div>
                <div class="footer">
                    <p>You're receiving this email because you added this item to your Fashion Finder watchlist.</p>
                    <p>To stop receiving alerts, remove the item from your watchlist.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Price Drop Alert!

        {product_name}

        Great news! An item on your watchlist just got cheaper at {shop_name}.

        Old price: {old_price:.2f} {currency}
        New price: {new_price:.2f} {currency}
        You save: {old_price - new_price:.2f} {currency} (-{drop_percent:.0f}%)

        View product: {product_url}

        ---
        You're receiving this email because you added this item to your Fashion Finder watchlist.
        """

        try:
            result = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            })

            return NotificationResult(
                success=True,
                message_id=result.get("id"),
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
            )

    def send_target_price_alert(
        self,
        to_email: str,
        product_name: str,
        shop_name: str,
        target_price: float,
        current_price: float,
        currency: str,
        product_url: str,
    ) -> NotificationResult:
        """
        Send alert when target price is reached.

        Args:
            to_email: Recipient email
            product_name: Name of the product
            shop_name: Shop where the product is sold
            target_price: User's target price
            current_price: Current price (at or below target)
            currency: Price currency
            product_url: Link to the product

        Returns:
            NotificationResult with success status
        """
        if not self.api_key:
            return NotificationResult(
                success=False,
                error="Resend API key not configured",
            )

        subject = f"Target Price Reached: {product_name} is now {current_price:.2f} {currency}!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .price-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
                .current-price {{ color: #28a745; font-size: 28px; font-weight: bold; }}
                .target-info {{ color: #666; margin-top: 10px; }}
                .cta-button {{
                    display: inline-block;
                    background: #28a745;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 15px;
                    font-size: 18px;
                }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Target Price Reached!</h1>
                </div>
                <div class="content">
                    <h2>{product_name}</h2>
                    <p>The item you've been waiting for is now at your target price at <strong>{shop_name}</strong>!</p>

                    <div class="price-box">
                        <p class="current-price">{current_price:.2f} {currency}</p>
                        <p class="target-info">Your target was {target_price:.2f} {currency}</p>
                    </div>

                    <p style="text-align: center;">
                        <a href="{product_url}" class="cta-button">Buy Now</a>
                    </p>
                </div>
                <div class="footer">
                    <p>You're receiving this email because you set a target price for this item.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Target Price Reached!

        {product_name}

        The item you've been waiting for is now at your target price at {shop_name}!

        Current price: {current_price:.2f} {currency}
        Your target was: {target_price:.2f} {currency}

        Buy now: {product_url}
        """

        try:
            result = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            })

            return NotificationResult(
                success=True,
                message_id=result.get("id"),
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
            )

    def send_back_in_stock_alert(
        self,
        to_email: str,
        product_name: str,
        shop_name: str,
        current_price: float,
        currency: str,
        product_url: str,
    ) -> NotificationResult:
        """
        Send alert when item is back in stock.

        Args:
            to_email: Recipient email
            product_name: Name of the product
            shop_name: Shop where the product is sold
            current_price: Current price
            currency: Price currency
            product_url: Link to the product

        Returns:
            NotificationResult with success status
        """
        if not self.api_key:
            return NotificationResult(
                success=False,
                error="Resend API key not configured",
            )

        subject = f"Back in Stock: {product_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ff9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .cta-button {{
                    display: inline-block;
                    background: #ff9800;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 15px;
                }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Back in Stock!</h1>
                </div>
                <div class="content">
                    <h2>{product_name}</h2>
                    <p>Good news! This item is back in stock at <strong>{shop_name}</strong>.</p>
                    <p>Current price: <strong>{current_price:.2f} {currency}</strong></p>

                    <p style="text-align: center;">
                        <a href="{product_url}" class="cta-button">View Product</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Items can sell out quickly, so don't wait too long!</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Back in Stock!

        {product_name}

        Good news! This item is back in stock at {shop_name}.
        Current price: {current_price:.2f} {currency}

        View product: {product_url}

        Items can sell out quickly, so don't wait too long!
        """

        try:
            result = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            })

            return NotificationResult(
                success=True,
                message_id=result.get("id"),
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                error=str(e),
            )


def process_price_checks(
    checks: list[PriceCheck],
    watchlist_items: dict[str, dict],
    notifier: Optional[EmailNotifier] = None,
) -> list[NotificationResult]:
    """
    Process price check results and send notifications.

    Args:
        checks: List of price check results
        watchlist_items: Dict of watchlist item ID -> item data (with user_email)
        notifier: Email notifier instance

    Returns:
        List of notification results
    """
    if notifier is None:
        notifier = EmailNotifier()

    results = []

    for check in checks:
        item = watchlist_items.get(check.watchlist_id)
        if not item:
            continue

        user_email = item.get("user_email")
        if not user_email:
            continue

        # Check if notification is warranted
        should_notify = False
        notification_type = None

        if check.target_price_reached:
            should_notify = True
            notification_type = "target"
        elif check.price_dropped and item.get("notify_any_drop", True):
            should_notify = True
            notification_type = "drop"

        if not should_notify:
            continue

        # Send notification
        shop_config = None
        from src.shops.registry import ShopRegistry
        shop_config = ShopRegistry.get_config(check.shop_id)
        shop_name = shop_config.display_name if shop_config else check.shop_id

        if notification_type == "target":
            result = notifier.send_target_price_alert(
                to_email=user_email,
                product_name=item.get("product_name", "Product"),
                shop_name=shop_name,
                target_price=float(item.get("target_price", 0)),
                current_price=float(check.new_price),
                currency=check.currency,
                product_url=item.get("product_url", ""),
            )
        else:  # price drop
            result = notifier.send_price_drop_alert(
                to_email=user_email,
                product_name=item.get("product_name", "Product"),
                shop_name=shop_name,
                old_price=float(check.old_price),
                new_price=float(check.new_price),
                currency=check.currency,
                product_url=item.get("product_url", ""),
                drop_percent=check.drop_percent,
            )

        results.append(result)

    return results
