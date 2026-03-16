"""
API Request/Response Models
----------------------------
Pydantic models for FastAPI endpoints defining
request shapes, response shapes, and validation.
"""

from pydantic import BaseModel, Field, HttpUrl
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
    ai_summary: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for the GET /api/health endpoint."""
    status: str
    version: str
    environment: str
    llm_available: bool
    total_jobs: int


class ExportRequest(BaseModel):
    """Query parameters for the GET /api/export endpoint."""
    format: str = Field("json", pattern="^(csv|json)$", description="Export format: csv or json")
