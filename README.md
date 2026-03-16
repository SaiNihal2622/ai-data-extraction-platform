# 🔮 Mindrift — AI Data Extraction Platform

A production-ready web scraping and data extraction platform with AI-assisted automation, data validation, and structured exports. Built to demonstrate expertise in Python web scraping, data processing, and AI engineering.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deployable-0B0D0E?style=flat-square&logo=railway&logoColor=white)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      USER / BROWSER                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Frontend Dashboard                     │
│         HTML + CSS + JavaScript (Dark Theme)            │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                       │
│          POST /scrape  GET /health  GET /export         │
└───────┬──────────┬──────────┬──────────┬────────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌───────────┐ ┌─────────┐ ┌──────┐ ┌──────────┐
│  Scraper  │ │Pipeline │ │ LLM  │ │Validation│
│  Engine   │ │Processor│ │Helper│ │  Engine   │
│           │ │         │ │      │ │           │
│ • Static  │ │ • Clean │ │ • AI │ │ • Missing │
│ • Dynamic │ │ • Dedup │ │  CSS │ │ • Dupes   │
│ • Crawl   │ │ • Norm  │ │  Sel │ │ • Format  │
└───────────┘ └────┬────┘ └──────┘ └──────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Export Layer   │
          │  CSV / JSON     │
          └────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Static Scraping** | BeautifulSoup + httpx for fast HTML extraction |
| **Dynamic Scraping** | Selenium with headless Chrome for JS-rendered sites |
| **Multi-page Crawling** | Follows links, handles pagination up to N pages |
| **Data Processing** | Pandas-powered cleaning, dedup, and normalization |
| **Validation Engine** | Automated quality checks with detailed reporting |
| **AI Assistance** | LLM-powered pattern detection and data summarization |
| **Structured Export** | Download results as CSV or JSON |
| **REST API** | Full FastAPI backend with Swagger docs |
| **Docker Support** | Production Dockerfile with Chromium included |
| **Railway Ready** | One-click deployment to Railway |

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mindrift.git
cd mindrift

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your API keys (optional)
```

### Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** to access the dashboard.

API docs available at **http://localhost:8000/docs**.

---

## API Reference

### `GET /api/health`
Returns service status and capabilities.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_available": false,
  "total_jobs": 0
}
```

### `POST /api/scrape`
Scrape a website and return extracted data.

**Request:**
```json
{
  "url": "https://quotes.toscrape.com",
  "use_dynamic": false,
  "use_llm": false,
  "max_pages": 5
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "url": "https://quotes.toscrape.com",
  "method": "static",
  "pages_crawled": 3,
  "items_extracted": 30,
  "data": [...],
  "validation": {
    "is_valid": true,
    "total_issues": 2,
    "issues": [...]
  }
}
```

### `GET /api/export/{job_id}?format=csv|json`
Download a previously scraped dataset.

---

## Project Structure

```
mindrift/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── api/
│   │   ├── models.py           # Pydantic request/response models
│   │   └── routes.py           # API endpoint definitions
│   ├── scraper/
│   │   ├── static_scraper.py   # BeautifulSoup + httpx scraper
│   │   ├── dynamic_scraper.py  # Selenium headless Chrome scraper
│   │   └── scraper_manager.py  # Scrape orchestration & job mgmt
│   ├── pipeline/
│   │   ├── processor.py        # Data cleaning & normalization
│   │   └── exporter.py         # CSV/JSON export engine
│   ├── validation/
│   │   └── validator.py        # Data quality validation engine
│   ├── llm/
│   │   └── assistant.py        # LLM-assisted extraction helper
│   └── frontend/
│       ├── index.html          # Dashboard UI
│       ├── style.css           # Dark theme styles
│       └── app.js              # Frontend logic
├── data/exports/               # Exported datasets
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## Docker Deployment

```bash
# Build the image
docker build -t mindrift .

# Run the container
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=your_key_here \
  mindrift
```

## Railway Deployment

1. Push the repo to GitHub
2. Connect the repo to [Railway](https://railway.app)
3. Add environment variables (`OPENROUTER_API_KEY`, etc.)
4. Deploy — Railway will use the Dockerfile automatically

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | No | — | OpenRouter API key for LLM features |
| `GEMINI_API_KEY` | No | — | Google Gemini API key (alternative) |
| `SELENIUM_HEADLESS` | No | `true` | Run Chrome headless |
| `MAX_PAGES` | No | `10` | Default max crawl pages |
| `PORT` | No | `8000` | Server port |

---

## Example Usage

### Scrape Quotes from a Website

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://quotes.toscrape.com", "max_pages": 3}'
```

### Export as CSV

```bash
curl -o data.csv "http://localhost:8000/api/export/JOB_ID?format=csv"
```

---

## Limitations

- Dynamic scraping requires Chromium (included in Docker image)
- LLM features require an OpenRouter API key
- In-memory job storage (resets on restart)
- Rate limiting not implemented (use responsibly)

## Future Improvements

- Redis-backed job queue for persistence
- Scheduled/recurring scrape jobs
- Custom CSS selector input in the UI
- Webhook notifications on completion
- User authentication and rate limiting
- FAISS-based vector search over extracted data

---

## License

MIT License — see [LICENSE](LICENSE) for details.
