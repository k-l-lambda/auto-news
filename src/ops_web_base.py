"""
WebCollectorBase - Base class for web collectors

Ported from Taranis AI's base_web_collector.py
Extends OperatorBase with web collection utilities including:
- HTTP requests with If-Modified-Since support
- XPath content extraction
- Trafilatura full article extraction
- Playwright browser mode for JS-rendered pages
- Digest splitting (extract multiple articles from index page)
- Proxy support
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

import dateutil.parser as dateparser
import lxml.html
import requests
from bs4 import BeautifulSoup, Tag
from trafilatura import extract, extract_metadata

from ops_base import OperatorBase
from playwright_manager import PlaywrightManager
import utils


class NoChangeError(Exception):
    """Raised when content has not changed (HTTP 304)"""
    pass


class WebCollectorBase(OperatorBase):
    """
    Base class for web collectors extending OperatorBase.
    Provides web scraping utilities for RSS and Web collectors.
    """

    def __init__(self):
        super().__init__()
        self.proxies: dict | None = None
        self.timeout: int = 60
        self.headers: dict = {"User-Agent": "Auto-News/1.0"}
        self.last_attempted: datetime | None = None

        # Browser mode settings
        self.browser_mode: bool = False
        self.playwright_manager: PlaywrightManager | None = None

        # Content extraction settings
        self.xpath: str = ""

        # Digest splitting settings
        self.digest_splitting: bool = False
        self.digest_splitting_limit: int = 30
        self.split_digest_urls: list = []

    def set_proxies(self, proxy_server: str | None):
        """Set proxy server for HTTP requests"""
        if proxy_server:
            self.proxies = {
                "http": proxy_server,
                "https": proxy_server,
                "ftp": proxy_server
            }
        else:
            self.proxies = None

    def update_headers(self, headers: str | dict):
        """Update request headers from JSON string or dict"""
        if isinstance(headers, str):
            try:
                headers_dict = json.loads(headers)
                if not isinstance(headers_dict, dict):
                    raise ValueError(f"ADDITIONAL_HEADERS must be a valid JSON object")
                self.headers.update(headers_dict)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"ADDITIONAL_HEADERS has to be valid JSON: {e}") from e
        elif isinstance(headers, dict):
            self.headers.update(headers)

    def set_user_agent(self, user_agent: str):
        """Set custom User-Agent header"""
        if user_agent:
            self.headers["User-Agent"] = user_agent

    def send_get_request(
        self,
        url: str,
        modified_since: datetime | None = None
    ) -> requests.Response:
        """
        Send a GET request to url with self.headers using self.proxies.

        Args:
            url: Target URL
            modified_since: If provided, make conditional request with If-Modified-Since

        Returns:
            Response object

        Raises:
            NoChangeError: If HTTP 304 (not modified)
            HTTPError: For other HTTP errors
        """
        request_headers = self.headers.copy()

        # Add If-Modified-Since header for conditional requests
        if modified_since:
            request_headers["If-Modified-Since"] = modified_since.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        print(f"[WebCollectorBase] GET {url}")
        response = requests.get(
            url,
            headers=request_headers,
            proxies=self.proxies,
            timeout=self.timeout
        )

        if response.status_code == 200 and not response.content:
            print(f"[WebCollectorBase] Response 200 OK but no content: {url}")

        if response.status_code == 304:
            raise NoChangeError(f"{url} was not modified")

        if response.status_code == 429:
            raise requests.exceptions.HTTPError(
                "Got Response 429 Too Many Requests. Try decreasing refresh interval."
            )

        response.raise_for_status()
        return response

    def get_last_modified(self, response: requests.Response) -> datetime | None:
        """Extract Last-Modified datetime from response headers"""
        if last_modified := response.headers.get("Last-Modified"):
            return dateparser.parse(last_modified, ignoretz=True)
        return None

    def init_playwright(self):
        """Initialize Playwright browser if browser_mode is enabled"""
        if self.browser_mode and not self.playwright_manager:
            self.playwright_manager = PlaywrightManager(
                proxies=self.proxies,
                headers=self.headers
            )

    def stop_playwright(self):
        """Stop Playwright browser if running"""
        if self.playwright_manager:
            self.playwright_manager.stop_playwright_if_needed()
            self.playwright_manager = None

    def fetch_article_content(
        self,
        url: str,
        xpath: str = ""
    ) -> tuple[str, datetime | None]:
        """
        Fetch article content from URL.

        Uses Playwright if browser_mode is enabled, otherwise uses requests.

        Args:
            url: Article URL
            xpath: Optional XPath to wait for/extract specific element

        Returns:
            Tuple of (html_content, published_date)
        """
        if self.browser_mode:
            self.init_playwright()
            if self.playwright_manager:
                content = self.playwright_manager.fetch_content_with_js(url, xpath)
                return content, None

        response = self.send_get_request(url, self.last_attempted)

        if not response.text:
            return "", None

        published_date = self.get_last_modified(response)
        return response.text, published_date

    def xpath_extraction(
        self,
        html_content: str,
        xpath: str,
        get_text: bool = True
    ) -> str | None:
        """
        Extract content using XPath.

        Args:
            html_content: HTML string
            xpath: XPath expression
            get_text: If True, return text content; otherwise return HTML

        Returns:
            Extracted content or None if not found
        """
        print(f"[WebCollectorBase] XPath extraction: {xpath}")
        try:
            document = lxml.html.fromstring(html_content)
            elements = document.xpath(xpath)

            if not elements:
                print(f"[WebCollectorBase] No content found for XPath: {xpath}")
                return None

            first_element = elements[0]
            if get_text:
                return first_element.text_content()

            return lxml.html.tostring(first_element, encoding='unicode')

        except Exception as e:
            print(f"[WebCollectorBase] XPath extraction error: {e}")
            return None

    def extract_meta(self, html_content: str, url: str) -> tuple[str, str]:
        """
        Extract metadata (author, title) from HTML using trafilatura.

        Args:
            html_content: HTML string
            url: Source URL

        Returns:
            Tuple of (author, title)
        """
        metadata = extract_metadata(html_content, default_url=url)
        if metadata is None:
            return "", ""

        meta_dict = metadata.as_dict()
        author = meta_dict.get("author", "") or ""
        title = meta_dict.get("title", "") or ""

        return author, title

    def extract_web_content(self, url: str, xpath: str = "") -> dict[str, Any]:
        """
        Extract full article content from URL using trafilatura.

        Args:
            url: Article URL
            xpath: Optional XPath for content extraction

        Returns:
            Dict with keys: author, title, content, published_date, language
        """
        html_content, published_date = self.fetch_article_content(url)

        if not html_content:
            return {
                "author": "",
                "title": "",
                "content": "",
                "published_date": None,
                "language": ""
            }

        # Extract content using XPath or trafilatura
        content = ""
        if xpath:
            content = self.xpath_extraction(html_content, xpath) or ""
        else:
            content = extract(html_content, url=url) or ""

        if not content:
            return {
                "author": "",
                "title": "",
                "content": "",
                "published_date": published_date,
                "language": ""
            }

        # Extract metadata
        author, title = self.extract_meta(html_content, url)

        return {
            "author": author,
            "title": title,
            "content": content,
            "published_date": published_date,
            "language": ""
        }

    def clean_url(self, url: str) -> str:
        """Remove query params and fragments from URL"""
        return url.split("?")[0].split("#")[0]

    def get_urls_from_html(self, base_url: str, html_content: str) -> list[str]:
        """
        Extract all URLs from HTML content.

        Args:
            base_url: Base URL for resolving relative links
            html_content: HTML string

        Returns:
            List of absolute URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        urls = []

        for a in soup.find_all("a", href=True):
            if isinstance(a, Tag) and a.has_attr("href"):
                href = a["href"]
                if isinstance(href, str):
                    absolute_url = urljoin(base_url, href)
                    urls.append(absolute_url)

        return urls

    def create_news_item(self, url: str, xpath: str = "") -> dict[str, Any]:
        """
        Create a news item dict from URL.

        Args:
            url: Article URL
            xpath: Optional XPath for content extraction

        Returns:
            News item dict
        """
        web_content = self.extract_web_content(url, xpath)

        # Generate hash for dedup
        for_hash = f"{web_content['author']}{web_content['title']}{self.clean_url(url)}"
        content_hash = hashlib.sha256(for_hash.encode()).hexdigest()

        return {
            "id": content_hash,
            "hash": content_hash,
            "author": web_content["author"],
            "title": web_content["title"],
            "content": web_content["content"],
            "url": url,
            "published_date": web_content["published_date"],
            "language": web_content["language"],
        }

    def parse_digests(self, index_url: str, xpath: str = "") -> list[dict]:
        """
        Parse digest/index page and extract individual articles.

        Fetches the index page, extracts all links, then fetches
        each linked article up to digest_splitting_limit.

        Args:
            index_url: URL of the index/digest page
            xpath: Optional XPath for content extraction

        Returns:
            List of news item dicts
        """
        if not self.digest_splitting:
            return []

        print(f"[WebCollectorBase] Parsing digest: {index_url}")

        # Fetch index page
        html_content, _ = self.fetch_article_content(index_url)
        if not html_content:
            return []

        # Extract URLs from index page
        self.split_digest_urls = self.get_urls_from_html(index_url, html_content)
        print(f"[WebCollectorBase] Found {len(self.split_digest_urls)} URLs in digest")

        # Fetch each article
        news_items = []
        max_items = min(len(self.split_digest_urls), self.digest_splitting_limit)

        for url in self.split_digest_urls[:max_items]:
            try:
                news_item = self.create_news_item(url, xpath)
                if news_item["content"]:  # Only add if content was extracted
                    news_items.append(news_item)
                    print(f"[WebCollectorBase] Extracted: {news_item['title'][:50]}...")
            except Exception as e:
                print(f"[WebCollectorBase] Failed to parse {url}: {e}")
                continue

        print(f"[WebCollectorBase] Extracted {len(news_items)} articles from digest")
        return news_items

    def configure_from_source(self, source: dict):
        """
        Configure collector from source parameters.

        Expected source dict format:
        {
            "url": "https://example.com/feed",
            "xpath": "//article",
            "browser_mode": True,
            "digest_splitting": True,
            "digest_limit": 30,
            "proxy": "http://proxy:8080",
            "user_agent": "Custom/1.0",
            "headers": {"Authorization": "Bearer xxx"}
        }
        """
        self.xpath = source.get("xpath", "")
        self.browser_mode = source.get("browser_mode", False)
        self.digest_splitting = source.get("digest_splitting", False)
        self.digest_splitting_limit = source.get("digest_limit", 30)

        if proxy := source.get("proxy"):
            self.set_proxies(proxy)

        if user_agent := source.get("user_agent"):
            self.set_user_agent(user_agent)

        if headers := source.get("headers"):
            self.update_headers(headers)

    def __del__(self):
        """Cleanup Playwright on destruction"""
        self.stop_playwright()
