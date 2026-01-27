"""Shop adapters for different integration types."""

from .feed_adapter import FeedAdapter
from .scraper_adapter import ScraperAdapter

__all__ = [
    "FeedAdapter",
    "ScraperAdapter",
]
