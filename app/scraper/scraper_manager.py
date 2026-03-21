"""
Scraper Manager Module
-----------------------
Orchestrates static and dynamic scraping with batch processing,
retry logic, progress tracking, and failure categorization.
"""

import asyncio
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

from app.scraper.static_scraper import StaticScraper
from app.scraper.dynamic_scraper import DynamicScraper

logger = logging.getLogger(__name__)


class ScrapeResult:
    """Container for scrape session results."""

    def __init__(self, job_id: str, url: str):
        self.job_id = job_id
        self.url = url
        self.pages: list[dict] = []
        self.all_items: list[dict] = []
        self.method: str = "static"
        self.started_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "url": self.url,
            "method": self.method,
            "pages_crawled": len(self.pages),
            "items_extracted": len(self.all_items),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "data": self.all_items if self.all_items else self.pages,
        }


class BatchResult:
    """Container for batch scrape results."""

    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.url_results: list[dict] = []  # per-URL status
        self.all_items: list[dict] = []
        self.completed: int = 0
        self.failed: int = 0

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "total_urls": len(self.url_results),
            "completed": self.completed,
            "failed": self.failed,
            "total_items": len(self.all_items),
            "url_results": self.url_results,
        }


class ScraperManager:
    """
    Orchestrator for scraping operations with batch processing and retry.
    """

    _results: dict[str, ScrapeResult] = {}
    _batch_results: dict[str, BatchResult] = {}

    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 3, 5]  # seconds

    def __init__(self):
        self.static_scraper = StaticScraper()

    async def scrape(
        self,
        url: str,
        use_dynamic: bool = False,
        max_pages: int = 5,
    ) -> ScrapeResult:
        """Execute a single scrape job with retry logic."""
        job_id = str(uuid.uuid4())[:8]
        result = ScrapeResult(job_id=job_id, url=url)

        logger.info(f"Starting scrape job {job_id} for {url} (dynamic={use_dynamic})")

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    wait = self.RETRY_BACKOFF[min(attempt - 1, len(self.RETRY_BACKOFF) - 1)]
                    logger.info(f"Retry {attempt}/{self.MAX_RETRIES} for {url} after {wait}s")
                    await asyncio.sleep(wait)

                if use_dynamic:
                    result.method = "dynamic"
                    result.pages = self._scrape_dynamic(url)
                else:
                    result.method = "static"
                    result.pages = await self._scrape_static(url, max_pages)

                    # Auto-fallback to dynamic if static yields nothing
                    total_items = sum(len(p.get("extracted_items", [])) for p in result.pages)
                    if total_items == 0 and len(result.pages) <= 1:
                        has_js = any(
                            p.get("title", "") == "" and len(p.get("paragraphs", [])) == 0
                            for p in result.pages
                        )
                        if has_js:
                            logger.info(f"Static yielded no data, falling back to dynamic for {url}")
                            result.method = "dynamic"
                            result.pages = self._scrape_dynamic(url)

                # Success — break retry loop
                last_error = None
                break

            except Exception as e:
                last_error = self._categorize_error(e)
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {last_error}")

        if last_error:
            result.error = last_error
        else:
            # Aggregate items
            self._aggregate_items(result)

        result.completed_at = datetime.now(timezone.utc)
        self._results[job_id] = result

        logger.info(
            f"Scrape job {job_id} {'failed' if result.error else 'completed'}: "
            f"{len(result.pages)} pages, {len(result.all_items)} items"
        )
        return result

    async def scrape_batch(
        self,
        urls: list[str],
        use_dynamic: bool = False,
        use_llm: bool = False,
        max_pages: int = 3,
    ) -> BatchResult:
        """
        Execute batch scraping across multiple URLs with retry and tracking.

        Args:
            urls: List of target URLs.
            use_dynamic: Force dynamic scraping.
            use_llm: Use LLM assistance.
            max_pages: Max pages per URL.

        Returns:
            BatchResult with per-URL status and aggregated data.
        """
        batch_id = str(uuid.uuid4())[:8]
        batch = BatchResult(batch_id=batch_id)

        logger.info(f"Starting batch {batch_id} with {len(urls)} URLs")

        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                continue

            url_status = {
                "url": url,
                "status": "processing",
                "items_extracted": 0,
                "error": None,
                "retries": 0,
            }

            try:
                result = await self.scrape(url=url, use_dynamic=use_dynamic, max_pages=max_pages)

                if result.error:
                    url_status["status"] = "failed"
                    url_status["error"] = result.error
                    url_status["retries"] = self.MAX_RETRIES
                    batch.failed += 1
                else:
                    url_status["status"] = "success"
                    url_status["items_extracted"] = len(result.all_items)
                    batch.all_items.extend(result.all_items)
                    batch.completed += 1

            except Exception as e:
                url_status["status"] = "failed"
                url_status["error"] = str(e)
                batch.failed += 1
                logger.error(f"Batch URL failed: {url} — {e}")

            batch.url_results.append(url_status)

        self._batch_results[batch_id] = batch

        logger.info(
            f"Batch {batch_id} done: {batch.completed}/{len(urls)} succeeded, "
            f"{len(batch.all_items)} total items"
        )
        return batch

    def _aggregate_items(self, result: ScrapeResult) -> None:
        """Aggregate all extracted items from pages into result.all_items."""
        for page in result.pages:
            items = page.get("extracted_items", [])
            for item in items:
                item["_source_url"] = page.get("url", result.url)
                result.all_items.append(item)

        # Flatten page data if no repeating items found
        if not result.all_items:
            for page in result.pages:
                flat_item = {
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "description": page.get("meta_description", ""),
                    "headings": "; ".join(h["text"] for h in page.get("headings", [])),
                    "content": " ".join(page.get("paragraphs", [])[:3]),
                    "links_count": len(page.get("links", [])),
                    "tables_count": len(page.get("tables", [])),
                }
                result.all_items.append(flat_item)

            for page in result.pages:
                for table in page.get("tables", []):
                    result.all_items.extend(table)

    @staticmethod
    def _categorize_error(error: Exception) -> str:
        """Categorize errors for better tracking and reporting."""
        msg = str(error).lower()
        if "timeout" in msg or "timed out" in msg:
            return f"TIMEOUT: {error}"
        elif "dns" in msg or "name resolution" in msg or "getaddrinfo" in msg:
            return f"DNS_ERROR: {error}"
        elif "403" in msg or "forbidden" in msg or "blocked" in msg:
            return f"BLOCKED: {error}"
        elif "404" in msg or "not found" in msg:
            return f"NOT_FOUND: {error}"
        elif "ssl" in msg or "certificate" in msg:
            return f"SSL_ERROR: {error}"
        elif "connection" in msg:
            return f"CONNECTION_ERROR: {error}"
        else:
            return f"PARSE_ERROR: {error}"

    async def _scrape_static(self, url: str, max_pages: int) -> list[dict]:
        """Run static scraping."""
        try:
            pages = await self.static_scraper.crawl(url, max_pages=max_pages)
            return pages
        finally:
            await self.static_scraper.close()

    def _scrape_dynamic(self, url: str) -> list[dict]:
        """Run dynamic scraping with Selenium."""
        scraper = DynamicScraper(headless=True)
        try:
            data = scraper.extract_page_data(url, use_scroll=True)
            return [data]
        finally:
            scraper.close()

    @classmethod
    def get_result(cls, job_id: str) -> Optional[ScrapeResult]:
        return cls._results.get(job_id)

    @classmethod
    def get_batch_result(cls, batch_id: str) -> Optional[BatchResult]:
        return cls._batch_results.get(batch_id)

    @classmethod
    def list_jobs(cls) -> list[dict]:
        return [
            {
                "job_id": r.job_id,
                "url": r.url,
                "method": r.method,
                "items": len(r.all_items),
                "status": "error" if r.error else "completed",
            }
            for r in cls._results.values()
        ]
