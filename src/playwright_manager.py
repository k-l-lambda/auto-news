"""
Playwright browser automation manager for web scraping.

Ported from Taranis AI's playwright_manager.py with adaptations for Auto-News.
"""

from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, TimeoutError, sync_playwright


class PlaywrightManager:
    """
    Manages Playwright browser instance for JavaScript-rendered page scraping.

    Usage:
        manager = PlaywrightManager()
        content = manager.fetch_content_with_js("https://example.com")
        manager.stop_playwright_if_needed()
    """

    def __init__(self, proxies: dict | None = None, headers: dict | None = None) -> None:
        """
        Initialize Playwright with optional proxy and headers.

        Args:
            proxies: Dict with http/https proxy URLs, e.g. {"http": "http://proxy:8080"}
            headers: Additional HTTP headers to send with requests
        """
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            proxy=self._parse_proxies(proxies)
        )
        self.context = self._setup_context(headers)
        self.page = self.context.new_page()

    def _setup_context(self, headers: dict | None = None) -> BrowserContext:
        """Create browser context with optional extra headers."""
        if headers and None not in headers.values():
            return self.browser.new_context(extra_http_headers=headers)
        return self.browser.new_context()

    def _parse_proxies(self, proxies: dict | None = None) -> dict | None:
        """Parse proxy dict into Playwright proxy format."""
        http_proxy = proxies.get("http") if proxies else None
        if not http_proxy:
            return None

        parsed_url = urlparse(http_proxy)
        username = parsed_url.username or ""
        password = parsed_url.password or ""

        print(f"[PlaywrightManager] Setting up proxy: {parsed_url.hostname}")

        return {
            "server": http_proxy,
            "username": username,
            "password": password
        }

    def fetch_content_with_js(self, url: str, xpath: str = "", timeout: int = 30000) -> str:
        """
        Fetch page content after JavaScript execution.

        Args:
            url: The URL to fetch
            xpath: Optional XPath to wait for specific element
            timeout: Page load timeout in milliseconds

        Returns:
            HTML content of the page
        """
        print(f"[PlaywrightManager] Fetching with JS: {url}, xpath={xpath}")

        try:
            self.page.goto(url, timeout=timeout)

            if xpath:
                # Wait for specific element if XPath provided
                locator = self.page.locator(f"xpath={xpath}")
                locator.wait_for(state="visible", timeout=timeout)
            else:
                # Wait for network to be idle
                self.page.wait_for_load_state("networkidle", timeout=timeout)

            return self.page.content() or ""

        except TimeoutError as e:
            print(f"[PlaywrightManager] Timeout fetching {url}: {e}")
            # Return whatever content we have
            return self.page.content() or ""

        except Exception as e:
            print(f"[PlaywrightManager] Error fetching {url}: {e}")
            return ""

    def stop_playwright_if_needed(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self.context:
                self.context.close()
                print("[PlaywrightManager] Context closed")
        except Exception as e:
            print(f"[PlaywrightManager] Error closing context: {e}")

        try:
            if self.browser:
                self.browser.close()
                print("[PlaywrightManager] Browser closed")
        except Exception as e:
            print(f"[PlaywrightManager] Error closing browser: {e}")

        try:
            if self.playwright:
                self.playwright.stop()
                print("[PlaywrightManager] Playwright stopped")
        except Exception as e:
            print(f"[PlaywrightManager] Error stopping playwright: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.stop_playwright_if_needed()
        return False
