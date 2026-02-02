"""Shop adapter registry for discovering and managing shop integrations."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

import yaml

from .base import ShopAdapter, ShopConfig, ShopRegion


class ShopRegistry:
    """Registry for shop adapters."""

    _adapters: Dict[str, ShopAdapter] = {}
    _configs: Dict[str, ShopConfig] = {}
    _adapter_classes: Dict[str, Type[ShopAdapter]] = {}

    @classmethod
    def register_adapter_class(cls, adapter_type: str, adapter_class: Type[ShopAdapter]):
        """Register an adapter class for a given type."""
        cls._adapter_classes[adapter_type] = adapter_class

    @classmethod
    def load_configs(cls, config_dir: Optional[Union[str, Path]] = None) -> Dict[str, ShopConfig]:
        """
        Load shop configurations from YAML files.

        Args:
            config_dir: Directory containing shop YAML files.
                       Defaults to src/config/shops/

        Returns:
            Dictionary of shop_id -> ShopConfig
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config" / "shops"
        else:
            config_dir = Path(config_dir)

        if not config_dir.exists():
            return {}

        configs = {}
        for yaml_file in config_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                config = cls._parse_config(data)
                configs[config.id] = config
                cls._configs[config.id] = config

            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")

        return configs

    @classmethod
    def _parse_config(cls, data: dict) -> ShopConfig:
        """Parse a YAML config dict into a ShopConfig."""
        from decimal import Decimal

        region_str = data.get("region", "EU")
        region = ShopRegion(region_str) if region_str in ShopRegion.__members__ else ShopRegion.EU

        return ShopConfig(
            id=data["id"],
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            url=data["url"],
            region=region,
            currency=data.get("currency", "SEK"),
            trust_score=float(data.get("trust_score", 0.8)),
            feed_url=data.get("feed", {}).get("url"),
            feed_type=data.get("feed", {}).get("type"),
            feed_mapping=data.get("feed", {}).get("mapping", {}),
            affiliate_network=data.get("affiliate", {}).get("network"),
            affiliate_id=data.get("affiliate", {}).get("id"),
            affiliate_url_template=data.get("affiliate", {}).get("url_template"),
            free_shipping_threshold=Decimal(str(data["shipping"]["free_threshold"]))
            if data.get("shipping", {}).get("free_threshold")
            else None,
            base_shipping_cost=Decimal(str(data["shipping"]["base_cost"]))
            if data.get("shipping", {}).get("base_cost")
            else None,
            ships_to_sweden=data.get("shipping", {}).get("ships_to_sweden", True),
        )

    @classmethod
    def get_adapter(cls, shop_id: str) -> Optional[ShopAdapter]:
        """
        Get or create an adapter for a shop.

        Args:
            shop_id: The shop identifier

        Returns:
            ShopAdapter instance or None if shop not found
        """
        if shop_id in cls._adapters:
            return cls._adapters[shop_id]

        config = cls._configs.get(shop_id)
        if not config:
            return None

        # Use specific adapters for certain shops
        if shop_id == "zalando_se":
            from .adapters.zalando_adapter import ZalandoAdapter
            adapter = ZalandoAdapter(config)
        elif shop_id == "kidsbrandstore_se":
            # Use Playwright scraper for JavaScript-rendered site
            from .adapters.kidsbrandstore_playwright import KidsbrandstorePlaywright
            adapter = KidsbrandstorePlaywright(config)
        else:
            # Determine adapter type based on feed configuration
            adapter_type = config.feed_type or "feed"

            adapter_class = cls._adapter_classes.get(adapter_type)
            if not adapter_class:
                # Fall back to feed adapter
                from .adapters.feed_adapter import FeedAdapter
                adapter_class = FeedAdapter

            adapter = adapter_class(config)

        cls._adapters[shop_id] = adapter
        return adapter

    @classmethod
    def get_all_adapters(cls) -> List[ShopAdapter]:
        """Get adapters for all configured shops."""
        adapters = []
        for shop_id in cls._configs:
            adapter = cls.get_adapter(shop_id)
            if adapter:
                adapters.append(adapter)
        return adapters

    @classmethod
    def get_config(cls, shop_id: str) -> Optional[ShopConfig]:
        """Get configuration for a shop."""
        return cls._configs.get(shop_id)

    @classmethod
    def get_all_configs(cls) -> List[ShopConfig]:
        """Get all shop configurations."""
        return list(cls._configs.values())

    @classmethod
    def clear(cls):
        """Clear all registered adapters and configs (for testing)."""
        cls._adapters.clear()
        cls._configs.clear()


# Auto-load configs on module import
def _initialize():
    """Initialize the registry with default configs."""
    ShopRegistry.load_configs()


_initialize()
