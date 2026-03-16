"""
Scraper Manager Module
-----------------------
Orchestrates static and dynamic scraping, auto-detects the appropriate
method, and manages scrape sessions with result aggregation.
"""

import logging
import uuid
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
        """Convert result to a serializable dictionary."""
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


class ScraperManager:
    """
    Orchestrator for scraping operations.

    Auto-detects whether to use static or dynamic scraping and
    manages the full scrape lifecycle.
    """

    # Store results in memory (would use Redis/DB in production)
    _results: dict[str, ScrapeResult] = {}

    def __init__(self):
        self.static_scraper = StaticScraper()

    async def scrape(
        self,
        url: str,
        use_dynamic: bool = False,
        max_pages: int = 5,
    ) -> ScrapeResult:
        """
        Execute a scrape job.

        Args:
            url: Target URL to scrape.
            use_dynamic: Force dynamic (Selenium) scraping.
            max_pages: Maximum pages to crawl.

        Returns:
            ScrapeResult with extracted data.
        """
        job_id = str(uuid.uuid4())[:8]
        result = ScrapeResult(job_id=job_id, url=url)

        logger.info(f"Starting scrape job {job_id} for {url} (dynamic={use_dynamic})")

        try:
            if use_dynamic:
                result.method = "dynamic"
                result.pages = self._scrape_dynamic(url)
            else:
                # Try static first
                result.method = "static"
                result.pages = await self._scrape_static(url, max_pages)

                # If minimal data extracted, try dynamic as fallback
                total_items = sum(
                    len(p.get("extracted_items", []))
                    for p in result.pages
                )
                if total_items == 0 and len(result.pages) <= 1:
                    has_js_indicators = any(
                        p.get("title", "") == "" and len(p.get("paragraphs", [])) == 0
                        for p in result.pages
                    )
                    if has_js_indicators:
                        logger.info(f"Static scraping yielded minimal data, trying dynamic for {url}")
                        result.method = "dynamic"
                        result.pages = self._scrape_dynamic(url)

            # Aggregate all extracted items across pages
            for page in result.pages:
                items = page.get("extracted_items", [])
                for item in items:
                    item["_source_url"] = page.get("url", url)
                    result.all_items.append(item)

            # If no repeating items found, flatten page data as items
            if not result.all_items:
                for page in result.pages:
                    flat_item = {
                        "url": page.get("url", ""),
                        "title": page.get("title", ""),
                        "description": page.get("meta_description", ""),
                        "headings": "; ".join(
                            h["text"] for h in page.get("headings", [])
                        ),
                        "content": " ".join(page.get("paragraphs", [])[:3]),
                        "links_count": len(page.get("links", [])),
                        "tables_count": len(page.get("tables", [])),
                    }
                    result.all_items.append(flat_item)

                # Also include table data as items if available
                for page in result.pages:
                    for table in page.get("tables", []):
                        result.all_items.extend(table)

            result.completed_at = datetime.now(timezone.utc)
            logger.info(
                f"Scrape job {job_id} completed: {len(result.pages)} pages, "
                f"{len(result.all_items)} items extracted"
            )

        except Exception as e:
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            logger.error(f"Scrape job {job_id} failed: {e}")

        # Store result
        self._results[job_id] = result
        return result

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
        """Retrieve a stored scrape result by job ID."""
        return cls._results.get(job_id)

    @classmethod
    def list_jobs(cls) -> list[dict]:
        """List all stored scrape jobs."""
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
