"""
API Routes
-----------
FastAPI endpoint definitions for scraping, batch processing,
data export, health checks, and AI-assisted analysis.
"""

import logging
from typing import Optional
from urllib.parse import quote

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.models import (
    ScrapeRequest, ScrapeResponse, HealthResponse,
    BatchScrapeRequest, BatchScrapeResponse, BatchUrlResult,
)
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
    """Health check — returns service status and capabilities."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        environment="production",
        llm_available=llm_assistant.is_available,
        total_jobs=len(ScraperManager.list_jobs()),
    )


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_website(request: ScrapeRequest):
    """
    Scrape a website and return extracted, processed, validated data.

    Pipeline: Crawl → Extract → Process → Validate → (AI Enrich) → Export
    """
    logger.info(f"Scrape request: url={request.url}, dynamic={request.use_dynamic}, llm={request.use_llm}")

    try:
        # Step 1: Scrape with retry
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

        # Step 4: AI assistance (optional)
        ai_summary = None
        ai_quality = None
        if request.use_llm and llm_assistant.is_available:
            try:
                ai_summary = llm_assistant.summarize_data(result.all_items[:10])
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
                ai_summary = f"LLM analysis unavailable: {str(e)}"

            try:
                ai_quality = llm_assistant.quality_score(result.all_items[:10])
            except Exception as e:
                logger.warning(f"LLM quality scoring failed: {e}")

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
            validation_summary=validation_report.summary(),
            ai_summary=ai_summary,
            ai_quality_score=ai_quality,
            started_at=result.started_at.isoformat(),
            completed_at=result.completed_at.isoformat() if result.completed_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-scrape", response_model=BatchScrapeResponse)
async def batch_scrape(request: BatchScrapeRequest):
    """
    Batch scrape multiple URLs with per-URL status tracking.

    Pipeline: Batch URLs → Scrape Each (with retry) → Aggregate → Validate
    """
    logger.info(f"Batch scrape: {len(request.urls)} URLs, dynamic={request.use_dynamic}")

    try:
        manager = ScraperManager()
        batch = await manager.scrape_batch(
            urls=request.urls,
            use_dynamic=request.use_dynamic,
            use_llm=request.use_llm,
            max_pages=request.max_pages,
        )

        # Process aggregated data
        df = processor.process(batch.all_items)
        validation_report = validator.validate(df)

        # AI summary for batch
        ai_summary = None
        if request.use_llm and llm_assistant.is_available and batch.all_items:
            try:
                ai_summary = llm_assistant.summarize_data(batch.all_items[:10])
            except Exception as e:
                logger.warning(f"Batch LLM summarization failed: {e}")

        processed_data = df.to_dict(orient="records") if not df.empty else batch.all_items

        return BatchScrapeResponse(
            batch_id=batch.batch_id,
            total_urls=len(batch.url_results),
            completed=batch.completed,
            failed=batch.failed,
            total_items=len(processed_data),
            data=processed_data,
            url_results=[BatchUrlResult(**r) for r in batch.url_results],
            validation=validation_report.to_dict(),
            validation_summary=validation_report.summary(),
            ai_summary=ai_summary,
        )

    except Exception as e:
        logger.exception(f"Batch scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{job_id}")
async def export_dataset(
    job_id: str,
    format: str = Query("json", pattern="^(csv|json|gsheets)$"),
):
    """
    Export a previously scraped dataset as CSV, JSON, or Google Sheets.
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
    elif format == "gsheets":
        # Generate CSV and return a URL that opens Google Sheets with the data
        csv_data = df.to_csv(index=False)
        encoded = quote(csv_data)
        sheets_url = f"https://docs.google.com/spreadsheets/d/create"
        return {"sheets_url": sheets_url, "csv_data": csv_data, "records": len(df)}
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
    """Use LLM to analyze HTML and suggest extraction patterns."""
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
