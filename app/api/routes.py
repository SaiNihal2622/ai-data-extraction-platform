"""
API Routes
-----------
FastAPI endpoint definitions for scraping, health checks, and data export.
"""

import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.models import ScrapeRequest, ScrapeResponse, HealthResponse
from app.scraper.scraper_manager import ScraperManager
from app.pipeline.processor import DataProcessor
from app.pipeline.exporter import DataExporter
from app.validation.validator import DataValidator
from app.llm.assistant import LLMAssistant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])

# Shared instances
processor = DataProcessor()
exporter = DataExporter()
validator = DataValidator()
llm_assistant = LLMAssistant()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status, version, and capabilities.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment="production",
        llm_available=llm_assistant.is_available,
        total_jobs=len(ScraperManager.list_jobs()),
    )


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest):
    """
    Scrape a website and return extracted, processed, and validated data.

    This endpoint:
    1. Crawls the target URL (static or dynamic)
    2. Extracts structured data
    3. Processes and cleans the data
    4. Validates data quality
    5. Optionally uses LLM for enhanced extraction
    """
    logger.info(f"Scrape request: url={request.url}, dynamic={request.use_dynamic}, llm={request.use_llm}")

    try:
        # Step 1: Scrape
        manager = ScraperManager()
        result = await manager.scrape(
            url=request.url,
            use_dynamic=request.use_dynamic,
            max_pages=request.max_pages,
        )

        if result.error:
            raise HTTPException(status_code=500, detail=f"Scraping failed: {result.error}")

        # Step 2: Process
        df = processor.process(result.all_items)

        # Step 3: Validate
        validation_report = validator.validate(df)

        # Step 4: LLM assistance (optional)
        ai_summary = None
        if request.use_llm and llm_assistant.is_available:
            try:
                ai_summary = llm_assistant.summarize_data(result.all_items[:10])
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
                ai_summary = f"LLM analysis unavailable: {str(e)}"

        # Step 5: Prepare response
        processed_data = df.to_dict(orient="records") if not df.empty else result.all_items

        return ScrapeResponse(
            job_id=result.job_id,
            url=result.url,
            method=result.method,
            pages_crawled=len(result.pages),
            items_extracted=len(processed_data),
            data=processed_data,
            validation=validation_report.to_dict(),
            ai_summary=ai_summary,
            started_at=result.started_at.isoformat(),
            completed_at=result.completed_at.isoformat() if result.completed_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{job_id}")
async def export_dataset(
    job_id: str,
    format: str = Query("json", regex="^(csv|json)$"),
):
    """
    Export a previously scraped dataset as CSV or JSON.

    Args:
        job_id: The job ID from a previous scrape operation.
        format: Export format — 'csv' or 'json'.
    """
    result = ScraperManager.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    df = pd.DataFrame(result.all_items)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data available for export")

    if format == "csv":
        stream = exporter.to_csv_stream(df)
        return StreamingResponse(
            stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=export_{job_id}.csv"},
        )
    else:
        stream = exporter.to_json_stream(df)
        return StreamingResponse(
            stream,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=export_{job_id}.json"},
        )


@router.get("/jobs")
async def list_jobs():
    """List all scrape jobs."""
    return {"jobs": ScraperManager.list_jobs()}


@router.post("/analyze")
async def analyze_html(html: str = "", url: str = ""):
    """
    Use LLM to analyze HTML and suggest extraction patterns.

    Provide either raw HTML or a URL to fetch.
    """
    if not llm_assistant.is_available:
        raise HTTPException(
            status_code=503,
            detail="LLM service not configured. Set OPENROUTER_API_KEY environment variable.",
        )

    if not html and not url:
        raise HTTPException(status_code=400, detail="Provide either 'html' or 'url' parameter")

    if url and not html:
        from app.scraper.static_scraper import StaticScraper
        scraper = StaticScraper()
        try:
            soup = await scraper.fetch_page(url)
            html = str(soup)[:3000]
        finally:
            await scraper.close()

    patterns = llm_assistant.detect_patterns(html[:3000])
    return {"patterns": patterns}
