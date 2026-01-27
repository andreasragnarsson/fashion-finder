# Fashion Finder - Design Document

## Problem Statement

As parents of teenagers (13 and 11 years old), we spend significant time helping them find specific clothes they've seen on TikTok. The challenges:
- Identifying exact brands/items from screenshots
- Finding items across multiple Swedish/EU shops
- Comparing prices including shipping
- Verifying shop legitimacy (avoiding fakes)
- Tracking when items go on sale or back in stock

## Requirements

### Core Features (MVP)
1. **Image Upload & AI Analysis**
   - Upload TikTok/Instagram screenshots
   - AI identifies ALL items in an outfit (not just one)
   - User can select specific items or entire outfit

2. **Multi-Item Outfit Support**
   - Identify: cap, hoodie, pants, shoes, bags, accessories
   - Let user select which items to search for
   - Option: "Find similar outfit within budget X kr"

3. **Shop Search**
   - Search across curated Swedish/EU shops
   - Show price, stock status, shipping cost
   - Calculate total cost (price + shipping + customs if non-EU)
   - Trust/legitimacy scores for shops

4. **Watchlist & Alerts**
   - Watch individual items for price drops
   - Watch complete outfits for total budget target
   - Email notifications when targets are met
   - Track price history over time

5. **Budget Outfit Builder**
   - Input: screenshot + budget (e.g., 2000 kr)
   - Output: Multiple outfit options:
     - Exact match (may be over budget)
     - Best match within budget (same brands, some alternatives)
     - Budget saver (similar style, different brands)

### Future Features (Post-MVP)
- User accounts & family sharing
- Browser extension
- Affiliate revenue integration
- Mobile app

## Technical Architecture

### Cost-Optimized Stack (Free/Low-Cost)

| Component | Choice | Cost |
|-----------|--------|------|
| Frontend | Streamlit Cloud | Free |
| Backend | FastAPI on Render.com | Free tier |
| Database | Supabase (PostgreSQL) | Free tier (500MB) |
| AI Vision | Google Gemini 2.0 Flash | Free tier (1500/day) |
| Scheduling | GitHub Actions | Free |
| Email | Resend | Free (3000/month) |
| Product Data | Affiliate feeds | Free + revenue |

### Monthly Cost Projection
- MVP (personal use): $0
- 100 users: ~$8/month
- 1000 users: ~$75/month

## Shop Adapter System

### Key Design: Easy to Add Shops

Three types of shop integrations:

1. **Affiliate Feed Shops** (config only, ~10 min to add)
   - Zalando, Boozt, JD Sports, NA-KD, Nike, Adidas
   - Free product data from affiliate networks (Awin, Adtraction)
   - YAML config with column mappings

2. **Scraper Shops** (config + CSS selectors, ~30 min to add)
   - Caliroots, Hollywood, local shops without affiliate programs
   - YAML config with CSS selectors
   - Rate-limited, respectful scraping

3. **Custom Adapter** (Python code, when needed)
   - For shops with special requirements
   - Full control over search/stock check logic

### Initial Shops (MVP)
- Kidsbrandstore.se (affiliate)
- Farfetch.com (affiliate)
- Zalando.se (affiliate)
- Boozt.com (affiliate)
- Giglio.com (affiliate)

## Data Model

### Core Tables
```
shops
- id, name, base_url, type (affiliate_feed/scraper/api)
- affiliate_network, affiliate_id
- trust_score, ships_from, delivery_days, return_days

products (from affiliate feeds)
- id, shop_id, external_id
- name, brand, category, price, currency
- in_stock, url, image_url, sizes

watchlist
- id, user_id, item_name, brand, size
- target_price, notify_price_drop, notify_back_in_stock

outfits
- id, user_id, name, source_image, budget

outfit_items
- id, outfit_id, category, brand, item_name, size
- allow_alternatives, style_tags

price_snapshots
- id, watchlist_id, shop_id, price, in_stock, checked_at
```

## User Journeys

### Journey 1: Find Single Item
1. Upload screenshot → AI identifies all items
2. Select one item (e.g., "just the shoes")
3. Enter size
4. See results from all shops with prices/stock
5. Click through to buy or add to watchlist

### Journey 2: Find Complete Outfit
1. Upload screenshot → AI identifies all items
2. Click "Find all items"
3. Enter sizes for each category
4. See results grouped by item
5. Summary shows best total price combination

### Journey 3: Build Budget Outfit
1. Upload screenshot → AI identifies all items
2. Click "Build similar outfit" + set budget (e.g., 2000 kr)
3. System suggests 3 options:
   - Exact match (original items, may exceed budget)
   - Best match (same brands, alternatives where needed)
   - Budget saver (similar style, cheaper brands)
4. User can watch entire outfit for when total hits target

### Journey 4: Price Drop Alert
1. Add item/outfit to watchlist with target price
2. System checks prices 2x daily via GitHub Actions
3. When target reached, email notification sent
4. Email includes direct links to buy

## Project Structure

```
fashion-finder/
├── src/
│   ├── app.py                    # Streamlit frontend
│   ├── api/
│   │   ├── main.py               # FastAPI backend
│   │   └── routes/
│   │       ├── identify.py       # Image → AI → items
│   │       ├── search.py         # Search shops
│   │       ├── outfit.py         # Outfit builder
│   │       └── watchlist.py      # Monitoring
│   ├── core/
│   │   ├── vision.py             # Gemini Flash integration
│   │   ├── outfit_analyzer.py    # Multi-item identification
│   │   ├── budget_optimizer.py   # Find alternatives in budget
│   │   └── cost_calculator.py    # Total cost calculation
│   ├── shops/
│   │   ├── base.py               # ShopAdapter base class
│   │   ├── registry.py           # Auto-discover shops
│   │   ├── adapters/
│   │   │   ├── feed_adapter.py   # Generic affiliate feed
│   │   │   └── scraper_adapter.py # Generic scraper
│   │   └── utils/
│   │       ├── feed_parser.py
│   │       └── rate_limiter.py
│   ├── config/
│   │   └── shops/                # YAML configs per shop
│   │       ├── zalando.yaml
│   │       ├── boozt.yaml
│   │       └── ...
│   ├── monitor/
│   │   ├── price_checker.py
│   │   └── notifier.py
│   └── db/
│       └── models.py
├── .github/
│   └── workflows/
│       ├── import-feeds.yml      # Daily feed import
│       └── price-monitor.yml     # 2x daily price check
├── requirements.txt
├── .env.example
└── README.md
```

## AI Prompt for Outfit Analysis

```python
OUTFIT_ANALYSIS_PROMPT = """
Analyze this image and identify ALL visible clothing items and accessories.

For each item, provide:
1. Category (cap, hoodie, t-shirt, jacket, pants, shorts, shoes, bag, etc.)
2. Brand (if identifiable, or "Unknown")
3. Specific product name (if identifiable, or describe it)
4. Color(s)
5. Style tags (sporty, streetwear, casual, formal, vintage, etc.)
6. Estimated price range in SEK
7. Confidence level (high/medium/low)

Return as structured JSON with overall_style and color_palette.
"""
```

## Affiliate-Ready Design

URLs are structured to easily enable affiliate tracking later:
- Shop configs have affiliate_network, affiliate_id, tracking_param fields
- build_affiliate_url() method on each adapter
- Can flip a switch per shop to enable affiliate links
- Revenue potential: 5-15% commission on purchases

## Implementation Order

### Phase 1: Core MVP
1. Project setup + Supabase schema
2. Gemini Vision integration (multi-item identification)
3. 3 shop integrations (Zalando, Boozt, JD Sports feeds)
4. Streamlit UI: upload → identify → search → results
5. Basic watchlist + email alerts via GitHub Actions

### Phase 2: Outfit Features
6. Outfit analysis (identify all items)
7. Item selection UI
8. Budget outfit builder with alternatives
9. Outfit watchlist (track total price)

### Phase 3: Scale
10. Add more shops (5-10 more)
11. User accounts
12. Affiliate link activation
13. Chrome extension

## Notes

- Swedish VAT (25%) applies to non-EU purchases over certain thresholds
- Affiliate networks (Awin, Adtraction) provide free product feeds when you join
- Most shops have affiliate programs - this makes data collection free
- Shops without affiliates need scraping (more work, but keeps flexibility)
