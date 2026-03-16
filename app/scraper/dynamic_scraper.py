"""
Dynamic Website Scraper Module
-------------------------------
Uses Selenium with headless Chrome to scrape JavaScript-rendered pages.
Handles infinite scroll, AJAX content, and dynamic page interactions.
"""

import os
import time
import logging
from typing import Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)


class DynamicScraper:
    """Scraper for JavaScript-rendered pages using Selenium."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the dynamic scraper.

        Args:
            headless: Run Chrome in headless mode.
            timeout: Default wait timeout in seconds.
        """
        self.headless = headless
        self.timeout = timeout
        self._driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure a Chrome WebDriver instance."""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Standard production-safe flags
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Use system ChromeDriver if available (e.g., in Docker)
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        chrome_bin = os.environ.get("CHROME_BIN")

        if chrome_bin:
            options.binary_location = chrome_bin

        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
        else:
            # Use webdriver-manager for automatic driver management
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except Exception:
                service = Service()  # Fallback to PATH

        return webdriver.Chrome(service=service, options=options)

    @property
    def driver(self) -> webdriver.Chrome:
        """Get or create the WebDriver instance."""
        if self._driver is None:
            self._driver = self._create_driver()
        return self._driver

    def close(self):
        """Close the WebDriver and clean up resources."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def fetch_page(self, url: str, wait_for: Optional[str] = None) -> BeautifulSoup:
        """
        Load a page and return parsed HTML.

        Args:
            url: URL to load.
            wait_for: Optional CSS selector to wait for before parsing.

        Returns:
            Parsed BeautifulSoup document.
        """
        logger.info(f"Loading dynamic page: {url}")
        self.driver.get(url)

        if wait_for:
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for selector '{wait_for}' on {url}")

        # Wait for basic page load
        time.sleep(2)
        return BeautifulSoup(self.driver.page_source, "lxml")

    def handle_infinite_scroll(self, max_scrolls: int = 10, scroll_pause: float = 2.0) -> BeautifulSoup:
        """
        Handle infinite scroll pages by scrolling down and waiting for new content.

        Args:
            max_scrolls: Maximum number of scroll actions.
            scroll_pause: Seconds to wait between scrolls.

        Returns:
            Parsed BeautifulSoup of the fully loaded page.
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for scroll in range(max_scrolls):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)

            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info(f"Infinite scroll completed after {scroll + 1} scrolls")
                break
            last_height = new_height

        return BeautifulSoup(self.driver.page_source, "lxml")

    def click_load_more(self, button_selector: str, max_clicks: int = 10, pause: float = 2.0) -> BeautifulSoup:
        """
        Handle 'Load More' button patterns.

        Args:
            button_selector: CSS selector for the load-more button.
            max_clicks: Maximum times to click the button.
            pause: Seconds to wait between clicks.

        Returns:
            Parsed BeautifulSoup of the fully loaded page.
        """
        for click in range(max_clicks):
            try:
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
                )
                self.driver.execute_script("arguments[0].click();", button)
                time.sleep(pause)
                logger.info(f"Clicked load-more button ({click + 1})")
            except TimeoutException:
                logger.info(f"Load-more button no longer found after {click} clicks")
                break

        return BeautifulSoup(self.driver.page_source, "lxml")

    def wait_for_ajax(self, timeout: Optional[int] = None) -> None:
        """
        Wait for all AJAX requests to complete.

        Args:
            timeout: Custom timeout in seconds.
        """
        wait_timeout = timeout or self.timeout
        try:
            WebDriverWait(self.driver, wait_timeout).until(
                lambda d: d.execute_script(
                    "return (typeof jQuery === 'undefined') || (jQuery.active === 0)"
                )
            )
            # Also wait for fetch/XHR to settle
            time.sleep(1)
        except TimeoutException:
            logger.warning("Timeout waiting for AJAX completion")

    def extract_page_data(self, url: str, use_scroll: bool = False) -> dict:
        """
        Full extraction pipeline for a dynamic page.

        Args:
            url: URL to scrape.
            use_scroll: Whether to attempt infinite scroll.

        Returns:
            Dictionary of extracted data.
        """
        try:
            soup = self.fetch_page(url)

            if use_scroll:
                soup = self.handle_infinite_scroll()

            # Import the static scraper's extraction methods
            from app.scraper.static_scraper import StaticScraper
            static = StaticScraper()

            data = static.extract_structured_data(soup, url)
            repeating = static.extract_repeating_elements(soup, url)
            if repeating:
                data["extracted_items"] = repeating

            data["scrape_method"] = "dynamic"
            return data

        except WebDriverException as e:
            logger.error(f"WebDriver error scraping {url}: {e}")
            return {"url": url, "error": str(e), "scrape_method": "dynamic"}

    def __del__(self):
        """Cleanup on garbage collection."""
        self.close()
