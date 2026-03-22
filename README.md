# Mindrift — AI Data Production & Validation Platform

A production-grade platform for generating structured, validated datasets for AI training pipelines. Built with Python, FastAPI, and AI-assisted quality scoring — inspired by Toloka and Mindrift data production workflows.

> **Live Demo:** [Deployed on Railway](https://stunning-friendship-production-94b6.up.railway.app)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend Dashboard                     │
│  Pipeline Visualizer · Batch Input · Validation Display  │
├─────────────────────────────────────────────────────────┤
│                    FastAPI Server                         │
│  /api/scrape · /api/batch-scrape · /api/export · /docs   │
├──────────┬───────────┬────────────┬──────────────────────┤
│ Scraper  │ Pipeline  │ Validation │   LLM Assistant      │
│ Manager  │ Processor │   Engine   │   (OpenRouter)       │
├──────────┴───────────┴────────────┴──────────────────────┤
│  Static Scraper (httpx)  │  Dynamic Scraper (Selenium)   │
└──────────────────────────┴───────────────────────────────┘
```

## Features

### Data Collection
- **Static scraping** — httpx + BeautifulSoup for fast HTML parsing
- **Dynamic scraping** — Selenium with headless Chrome for JS-rendered pages
- **Batch processing** — scrape up to 20 URLs in a single pipeline run
- **Retry logic** — configurable retries with exponential backoff
- **Error categorization** — TIMEOUT, DNS, BLOCKED, NOT_FOUND, SSL, CONNECTION, PARSE

### Data Processing Pipeline
- Text cleaning & Unicode normalization
- Duplicate detection and removal
- Field normalization (URLs, empty values)
- Table extraction and structured data parsing

### Validation Engine
- **Missing values** — per-column null/empty detection with severity levels
- **Duplicate detection** — full-row and key-column duplicates
- **Schema validation** — detects mixed types in columns (numeric/non-numeric, date/non-date)
- **Format consistency** — catches inconsistent casing in categorical fields
- **URL/Email format** — validates URL and email patterns
- **Text quality** — flags very short or empty text fields
- **Structured summary** — JSON report with valid/invalid counts and issue categories

### AI Integration (via OpenRouter)
- **Dataset summarization** — AI-generated description of extracted data
- **Quality scoring** — 1-10 rating with justification, issues, and suggestions
- **Text cleaning** — LLM-powered cleanup of messy text
- **Data normalization** — AI standardization of formats and casing
- **Pattern detection** — automatic CSS selector suggestions

### Export
- **CSV** — standard comma-separated values
- **JSON** — pretty-printed JSON with full schema
- **Google Sheets** — download CSV and open Google Sheets for import

---

## Quick Start

### Prerequisites
- Python 3.11+
- Chrome/Chromium (for dynamic scraping)

### Install & Run
```bash
# Clone
git clone https://github.com/SaiNihal2622/ai-data-extraction-platform.git
cd ai-data-extraction-platform

# Install
pip install -r requirements.txt

# Configure (optional — for AI features)
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Run
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` to access the dashboard.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|------------|
| `/api/health` | GET | System health check |
| `/api/scrape` | POST | Single URL scrape with validation |
| `/api/batch-scrape` | POST | Batch scrape multiple URLs |
| `/api/export/{job_id}` | GET | Export dataset (CSV/JSON/Sheets) |
| `/api/jobs` | GET | List all scrape jobs |
| `/api/analyze` | POST | AI-powered HTML analysis |

### POST /api/scrape
```json
{
  "url": "https://quotes.toscrape.com",
  "use_dynamic": false,
  "use_llm": true,
  "max_pages": 5
}
```

### POST /api/batch-scrape
```json
{
  "urls": [
    "https://quotes.toscrape.com",
    "https://books.toscrape.com"
  ],
  "use_dynamic": false,
  "use_llm": true,
  "max_pages": 3
}
```

### Validation Summary Response
```json
{
  "total_records": 1000,
  "valid_records": 980,
  "invalid_records": 20,
  "issues": ["missing_fields", "duplicates", "format_errors"]
}
```

---

## Project Structure

```
mindrift/
├── app/
│   ├── api/
│   │   ├── models.py          # Pydantic request/response models
│   │   └── routes.py          # FastAPI endpoints
│   ├── scraper/
│   │   ├── static_scraper.py  # httpx + BeautifulSoup
│   │   ├── dynamic_scraper.py # Selenium headless Chrome
│   │   └── scraper_manager.py # Orchestrator + batch + retry
│   ├── pipeline/
│   │   ├── processor.py       # Data cleaning & normalization
│   │   └── exporter.py        # CSV/JSON export streams
│   ├── validation/
│   │   └── validator.py       # Schema + format + quality checks
│   ├── llm/
│   │   └── assistant.py       # AI quality scoring + cleaning
│   ├── frontend/
│   │   ├── index.html         # Dashboard UI
│   │   ├── style.css          # Dark theme + pipeline styling
│   │   └── app.js             # Frontend logic
│   └── main.py                # FastAPI app entry point
├── Dockerfile
├── railway.toml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Deployment

### Docker
```bash
docker build -t mindrift .
docker run -p 8000:8000 --env-file .env mindrift
```

### Railway
```bash
npm install -g @railway/cli
railway login
railway init
railway up --detach
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|------------|
| `OPENROUTER_API_KEY` | Optional | OpenRouter API key for AI features |
| `LLM_MODEL` | Optional | Model name (default: `google/gemini-2.0-flash-001`) |
| `SELENIUM_HEADLESS` | Optional | Force headless mode (default: `true`) |
| `PORT` | Auto | Set by Railway, defaults to 8000 |

---

## License

MIT
