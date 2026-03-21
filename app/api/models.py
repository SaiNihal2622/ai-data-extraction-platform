"""
API Request/Response Models
----------------------------
Pydantic models for FastAPI endpoints defining
request shapes, response shapes, and validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ScrapeRequest(BaseModel):
    """Request body for the POST /api/scrape endpoint."""
    url: str = Field(..., description="Target website URL to scrape")
    use_dynamic: bool = Field(False, description="Use Selenium for JavaScript-rendered pages")
    use_llm: bool = Field(False, description="Use LLM to assist with extraction")
    max_pages: int = Field(5, ge=1, le=50, description="Maximum pages to crawl")


class ScrapeResponse(BaseModel):
    """Response for the POST /api/scrape endpoint."""
    job_id: str
    url: str
    method: str
    pages_crawled: int
    items_extracted: int
    data: list[dict]
    validation: dict
    validation_summary: Optional[dict] = None
    ai_summary: Optional[str] = None
    ai_quality_score: Optional[dict] = None
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class BatchScrapeRequest(BaseModel):
    """Request body for POST /api/batch-scrape."""
    urls: list[str] = Field(..., min_length=1, max_length=20, description="List of URLs to scrape")
    use_dynamic: bool = Field(False, description="Use Selenium for JS pages")
    use_llm: bool = Field(False, description="Use LLM to assist")
    max_pages: int = Field(3, ge=1, le=20, description="Max pages per URL")


class BatchUrlResult(BaseModel):
    """Result for a single URL in a batch."""
    url: str
    status: str  # "success", "failed", "retrying"
    items_extracted: int = 0
    error: Optional[str] = None
    retries: int = 0


class BatchScrapeResponse(BaseModel):
    """Response for POST /api/batch-scrape."""
    batch_id: str
    total_urls: int
    completed: int
    failed: int
    total_items: int
    data: list[dict]
    url_results: list[BatchUrlResult]
    validation: dict
    validation_summary: Optional[dict] = None
    ai_summary: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for the GET /api/health endpoint."""
    status: str
    version: str
    environment: str
    llm_available: bool
    total_jobs: int


class ExportRequest(BaseModel):
    """Query parameters for the GET /api/export endpoint."""
    format: str = Field("json", pattern="^(csv|json|gsheets)$", description="Export format")
