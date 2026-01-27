# Fashion Finder

AI-powered fashion discovery tool that identifies clothing from screenshots and searches across Swedish/EU shops.

## Features

- **AI Vision Analysis**: Upload fashion screenshots and get AI-powered item identification using Google Gemini 2.0 Flash
- **Multi-Shop Search**: Search across 5+ Swedish/EU fashion retailers simultaneously
- **Price Comparison**: Compare prices including shipping, customs, and VAT for total cost
- **Watchlist**: Track items and get price drop alerts via email
- **Outfit Builder**: Build complete outfits within a budget

## Supported Shops

- Kidsbrandstore.se
- Farfetch.com
- Zalando.se
- Boozt.com
- Giglio.com

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI Vision**: Google Gemini 2.0 Flash
- **Email**: Resend
- **Scheduling**: GitHub Actions

## Setup

### 1. Clone and Install

```bash
git clone <repo-url>
cd fashion-finder
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Initialize Database

Run the SQL migrations in Supabase or use the provided schema.

### 4. Run the Application

**Start the API server:**
```bash
uvicorn src.api.main:app --reload
```

**Start the Streamlit frontend:**
```bash
streamlit run src/app.py
```

## Project Structure

```
fashion-finder/
├── src/
│   ├── app.py                  # Streamlit frontend
│   ├── api/
│   │   ├── main.py             # FastAPI application
│   │   └── routes/             # API endpoints
│   ├── core/
│   │   ├── vision.py           # Gemini AI integration
│   │   ├── outfit_analyzer.py  # Multi-item identification
│   │   └── cost_calculator.py  # Price + shipping + VAT
│   ├── shops/
│   │   ├── base.py             # Shop adapter base class
│   │   ├── registry.py         # Shop discovery
│   │   └── adapters/           # Shop-specific adapters
│   ├── config/
│   │   └── shops/              # Shop YAML configurations
│   ├── monitor/
│   │   ├── price_checker.py    # Watchlist price monitoring
│   │   └── notifier.py         # Email alerts
│   └── db/
│       └── models.py           # SQLAlchemy models
└── .github/
    └── workflows/              # Automated jobs
```

## API Endpoints

- `POST /identify` - Upload image and get AI analysis
- `POST /search` - Search shops for items
- `GET/POST/DELETE /watchlist` - Manage watchlist
- `GET/POST /outfits` - Manage saved outfits

## License

MIT
