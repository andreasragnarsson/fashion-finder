"""FastAPI application for Fashion Finder."""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.shops.registry import ShopRegistry

from .routes import identify, search, watchlist, outfit


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Load shop configurations
    ShopRegistry.load_configs()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Fashion Finder API",
    description="AI-powered fashion discovery and price comparison",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(identify.router, prefix="/api", tags=["Vision"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(watchlist.router, prefix="/api", tags=["Watchlist"])
app.include_router(outfit.router, prefix="/api", tags=["Outfits"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Fashion Finder API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/shops")
async def list_shops():
    """List all configured shops."""
    configs = ShopRegistry.get_all_configs()
    return {
        "shops": [
            {
                "id": c.id,
                "name": c.display_name,
                "url": c.url,
                "region": c.region.value,
                "currency": c.currency,
                "trust_score": c.trust_score,
                "ships_to_sweden": c.ships_to_sweden,
            }
            for c in configs
        ]
    }
