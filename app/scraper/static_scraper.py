"""
Static HTML Scraper Module
--------------------------
Uses httpx + BeautifulSoup to scrape static HTML pages.
Handles multi-page navigation, link extraction, and structured data extraction.
"""

import re
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class StaticScraper:
    """Scraper for static HTML pages using httpx and BeautifulSoup."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch a page and return parsed BeautifulSoup object.

        Args:
            url: The URL to fetch.

        Returns:
            Parsed BeautifulSoup document.

        Raises:
            httpx.HTTPError: If the request fails after retries.
        """
        client = await self._get_client()
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching {url} (attempt {attempt}/{self.max_retries})")
                response = await client.get(url)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed for {url}: {e}")

        raise last_error  # type: ignore

    def extract_links(self, soup: BeautifulSoup, base_url: str, same_domain: bool = True) -> list[str]:
        """
        Extract all links from a page.

        Args:
            soup: Parsed BeautifulSoup document.
            base_url: Base URL for resolving relative links.
            same_domain: If True, only return links on the same domain.

        Returns:
            List of absolute URLs.
        """
        links = []
        base_domain = urlparse(base_url).netloc

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            # Skip non-HTTP links
            if parsed.scheme not in ("http", "https"):
                continue

            # Filter by domain if requested
            if same_domain and parsed.netloc != base_domain:
                continue

            # Clean fragment and normalize
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            if clean_url not in links:
                links.append(clean_url)

        return links

    def extract_tables(self, soup: BeautifulSoup) -> list[list[dict[str, str]]]:
        """
        Extract all HTML tables as lists of row dictionaries.

        Args:
            soup: Parsed BeautifulSoup document.

        Returns:
            List of tables, each table is a list of row dicts.
        """
        tables_data = []

        for table in soup.find_all("table"):
            # Extract headers
            headers = []
            header_row = table.find("thead")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            else:
                first_row = table.find("tr")
                if first_row:
                    headers = [cell.get_text(strip=True) for cell in first_row.find_all(["th", "td"])]

            if not headers:
                headers = [f"column_{i}" for i in range(len(table.find("tr").find_all(["td", "th"])))]

            # Extract rows
            rows = []
            body = table.find("tbody") or table
            for tr in body.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) == len(headers):
                    row = {headers[i]: cells[i].get_text(strip=True) for i in range(len(headers))}
                    rows.append(row)

            if rows:
                tables_data.append(rows)

        return tables_data

    def extract_structured_data(self, soup: BeautifulSoup, url: str) -> dict:
        """
        Extract structured data from a page using common patterns.

        Extracts: title, meta description, headings, paragraphs, links,
        tables, lists, and any JSON-LD structured data.

        Args:
            soup: Parsed BeautifulSoup document.
            url: URL of the page.

        Returns:
            Dictionary of extracted data.
        """
        data: dict = {
            "url": url,
            "title": "",
            "meta_description": "",
            "headings": [],
            "paragraphs": [],
            "links": [],
            "tables": [],
            "lists": [],
            "images": [],
            "structured_data": [],
        }

        # Title
        title_tag = soup.find("title")
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and isinstance(meta, Tag):
            data["meta_description"] = meta.get("content", "")

        # Headings (h1 - h6)
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                if text:
                    data["headings"].append({"level": level, "text": text})

        # Paragraphs
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Filter trivial paragraphs
                data["paragraphs"].append(text)

        # Links
        data["links"] = self.extract_links(soup, url)

        # Tables
        data["tables"] = self.extract_tables(soup)

        # Lists
        for ul in soup.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li", recursive=False)]
            if items and len(items) > 1:
                data["lists"].append(items)

        # Images
        for img in soup.find_all("img", src=True):
            alt = img.get("alt", "")
            src = urljoin(url, img["src"])
            data["images"].append({"src": src, "alt": alt})

        # JSON-LD structured data
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                json_data = json.loads(script.string)
                data["structured_data"].append(json_data)
            except (json.JSONDecodeError, TypeError):
                pass

        return data

    def extract_repeating_elements(self, soup: BeautifulSoup, url: str) -> list[dict]:
        """
        Detect and extract repeating card/item patterns from a page.

        Looks for common patterns like article cards, product listings,
        quote blocks, etc. by finding repeated sibling elements with
        similar structure.

        Args:
            soup: Parsed BeautifulSoup document.
            url: URL of the page.

        Returns:
            List of extracted item dictionaries.
        """
        items = []

        # Strategy: look for repeated elements with common class patterns
        candidate_selectors = [
            "article", ".card", ".item", ".post", ".listing",
            ".product", ".result", ".entry", "[class*='quote']",
            "[class*='card']", "[class*='item']",
        ]

        for selector in candidate_selectors:
            try:
                elements = soup.select(selector)
            except Exception:
                continue

            if len(elements) >= 3:  # At least 3 repeating elements
                for elem in elements:
                    item: dict = {}

                    # Extract text from various child elements
                    heading = elem.find(["h1", "h2", "h3", "h4", "h5", "h6"])
                    if heading:
                        item["title"] = heading.get_text(strip=True)

                    # Description / body text
                    body = elem.find(["p", ".text", ".description", ".content"])
                    if body:
                        item["text"] = body.get_text(strip=True)

                    # Link
                    link = elem.find("a", href=True)
                    if link:
                        item["link"] = urljoin(url, link["href"])
                        if not item.get("title"):
                            item["title"] = link.get_text(strip=True)

                    # Image
                    img = elem.find("img", src=True)
                    if img:
                        item["image"] = urljoin(url, img["src"])

                    # Any spans with classes suggesting metadata
                    for span in elem.find_all("span"):
                        text = span.get_text(strip=True)
                        cls = " ".join(span.get("class", []))
                        if cls and text:
                            # Use the class name as a field key
                            key = re.sub(r'[^a-z0-9]', '_', cls.lower()).strip('_')
                            if key and len(key) < 30:
                                item[key] = text

                    if item:
                        items.append(item)

                if items:
                    break  # Use first successful selector

        return items

    async def crawl(self, start_url: str, max_pages: int = 5) -> list[dict]:
        """
        Crawl a website starting from the given URL.

        Args:
            start_url: Starting URL for the crawl.
            max_pages: Maximum number of pages to crawl.

        Returns:
            List of extracted data dictionaries (one per page).
        """
        visited: set[str] = set()
        to_visit: list[str] = [start_url]
        results: list[dict] = []

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)

            if url in visited:
                continue

            try:
                soup = await self.fetch_page(url)
                visited.add(url)

                # Extract structured data from this page
                page_data = self.extract_structured_data(soup, url)

                # Also try to extract repeating elements
                repeating = self.extract_repeating_elements(soup, url)
                if repeating:
                    page_data["extracted_items"] = repeating

                results.append(page_data)

                # Add new links to visit
                new_links = self.extract_links(soup, start_url, same_domain=True)
                for link in new_links:
                    if link not in visited:
                        to_visit.append(link)

                logger.info(f"Crawled {url}: {len(page_data.get('extracted_items', []))} items found")

            except Exception as e:
                logger.error(f"Failed to crawl {url}: {e}")

        return results
