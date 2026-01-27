"""SQLAlchemy models for Fashion Finder database."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    Numeric,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Currency(str, PyEnum):
    SEK = "SEK"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class ShopRegion(str, PyEnum):
    SE = "SE"  # Sweden
    EU = "EU"  # European Union (non-Sweden)
    NON_EU = "NON_EU"  # Outside EU


class Shop(Base):
    """Shop configuration and trust scores."""

    __tablename__ = "shops"

    id = Column(String(50), primary_key=True)  # e.g., "zalando_se"
    name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=False)
    region = Column(Enum(ShopRegion), nullable=False, default=ShopRegion.EU)
    currency = Column(Enum(Currency), nullable=False, default=Currency.SEK)
    trust_score = Column(Float, nullable=False, default=0.8)  # 0.0 to 1.0

    # Feed configuration
    feed_url = Column(Text, nullable=True)
    feed_type = Column(String(20), nullable=True)  # "csv", "xml", "api"

    # Affiliate info
    affiliate_network = Column(String(50), nullable=True)
    affiliate_id = Column(String(100), nullable=True)

    # Shipping info
    free_shipping_threshold = Column(Numeric(10, 2), nullable=True)
    base_shipping_cost = Column(Numeric(10, 2), nullable=True)
    ships_to_sweden = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_feed_import = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")


class Product(Base):
    """Product catalog from feeds."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(String(50), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(100), nullable=False)  # Shop's product ID

    # Product details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)  # Before discount
    currency = Column(Enum(Currency), nullable=False, default=Currency.SEK)

    # Attributes
    color = Column(String(50), nullable=True)
    sizes = Column(JSON, nullable=True)  # List of available sizes
    material = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)  # "men", "women", "unisex", "kids"

    # Media
    image_url = Column(Text, nullable=True)
    product_url = Column(Text, nullable=False)
    affiliate_url = Column(Text, nullable=True)

    # Search optimization
    search_text = Column(Text, nullable=True)  # Concatenated searchable text
    style_tags = Column(JSON, nullable=True)  # AI-generated style tags

    # Status
    in_stock = Column(Boolean, default=True)
    last_seen = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    shop = relationship("Shop", back_populates="products")
    price_snapshots = relationship("PriceSnapshot", back_populates="product", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shop_id", "external_id", name="uq_shop_product"),
        Index("ix_products_brand", "brand"),
        Index("ix_products_category", "category"),
        Index("ix_products_search", "search_text"),
    )


class WatchlistItem(Base):
    """User watchlist for price tracking."""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Alert settings
    target_price = Column(Numeric(10, 2), nullable=True)  # Alert when price drops below
    notify_any_drop = Column(Boolean, default=True)  # Alert on any price drop

    # Tracking
    price_at_add = Column(Numeric(10, 2), nullable=False)  # Price when added
    lowest_price_seen = Column(Numeric(10, 2), nullable=True)
    last_notified = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint("user_email", "product_id", name="uq_user_product"),
        Index("ix_watchlist_user", "user_email"),
    )


class Outfit(Base):
    """Saved outfit searches."""

    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False)

    # Outfit details
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source_image_url = Column(Text, nullable=True)  # Original uploaded image

    # AI analysis results
    ai_analysis = Column(JSON, nullable=True)  # Full Gemini response

    # Budget
    budget = Column(Numeric(10, 2), nullable=True)
    budget_currency = Column(Enum(Currency), default=Currency.SEK)

    # Status
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    items = relationship("OutfitItem", back_populates="outfit", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_outfits_user", "user_email"),)


class OutfitItem(Base):
    """Items within outfits."""

    __tablename__ = "outfit_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outfit_id = Column(Integer, ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False)

    # Item identification from AI
    item_type = Column(String(50), nullable=False)  # e.g., "jacket", "pants", "shoes"
    description = Column(Text, nullable=True)  # AI description
    brand_guess = Column(String(100), nullable=True)  # AI brand guess
    color = Column(String(50), nullable=True)
    style_tags = Column(JSON, nullable=True)  # AI style tags

    # User preferences
    size = Column(String(20), nullable=True)  # User's size for this category

    # Selected product (if user chose one)
    selected_product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Position in image (optional)
    bounding_box = Column(JSON, nullable=True)  # {"x": 0, "y": 0, "width": 100, "height": 100}

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    outfit = relationship("Outfit", back_populates="items")
    selected_product = relationship("Product")


class PriceSnapshot(Base):
    """Price history tracking."""

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    in_stock = Column(Boolean, default=True)

    captured_at = Column(DateTime, server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="price_snapshots")

    __table_args__ = (Index("ix_price_snapshots_product_date", "product_id", "captured_at"),)


# Supabase schema SQL for reference
SCHEMA_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Shops table
CREATE TABLE shops (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    region VARCHAR(10) NOT NULL DEFAULT 'EU',
    currency VARCHAR(3) NOT NULL DEFAULT 'SEK',
    trust_score FLOAT NOT NULL DEFAULT 0.8,
    feed_url TEXT,
    feed_type VARCHAR(20),
    affiliate_network VARCHAR(50),
    affiliate_id VARCHAR(100),
    free_shipping_threshold NUMERIC(10, 2),
    base_shipping_cost NUMERIC(10, 2),
    ships_to_sweden BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    last_feed_import TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    shop_id VARCHAR(50) NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    price NUMERIC(10, 2) NOT NULL,
    original_price NUMERIC(10, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'SEK',
    color VARCHAR(50),
    sizes JSONB,
    material VARCHAR(100),
    gender VARCHAR(20),
    image_url TEXT,
    product_url TEXT NOT NULL,
    affiliate_url TEXT,
    search_text TEXT,
    style_tags JSONB,
    in_stock BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(shop_id, external_id)
);

CREATE INDEX ix_products_brand ON products(brand);
CREATE INDEX ix_products_category ON products(category);
CREATE INDEX ix_products_search ON products USING gin(to_tsvector('english', search_text));

-- Watchlist table
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    target_price NUMERIC(10, 2),
    notify_any_drop BOOLEAN DEFAULT TRUE,
    price_at_add NUMERIC(10, 2) NOT NULL,
    lowest_price_seen NUMERIC(10, 2),
    last_notified TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_email, product_id)
);

CREATE INDEX ix_watchlist_user ON watchlist(user_email);

-- Outfits table
CREATE TABLE outfits (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    description TEXT,
    source_image_url TEXT,
    ai_analysis JSONB,
    budget NUMERIC(10, 2),
    budget_currency VARCHAR(3) DEFAULT 'SEK',
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_outfits_user ON outfits(user_email);

-- Outfit items table
CREATE TABLE outfit_items (
    id SERIAL PRIMARY KEY,
    outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL,
    description TEXT,
    brand_guess VARCHAR(100),
    color VARCHAR(50),
    style_tags JSONB,
    size VARCHAR(20),
    selected_product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    bounding_box JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Price snapshots table
CREATE TABLE price_snapshots (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    in_stock BOOLEAN DEFAULT TRUE,
    captured_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_price_snapshots_product_date ON price_snapshots(product_id, captured_at);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER shops_updated_at BEFORE UPDATE ON shops FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER watchlist_updated_at BEFORE UPDATE ON watchlist FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER outfits_updated_at BEFORE UPDATE ON outfits FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER outfit_items_updated_at BEFORE UPDATE ON outfit_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();
"""
