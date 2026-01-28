#!/usr/bin/env python3
"""
Test Web Collector functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


def test_imports():
    """Test that all modules can be imported"""
    print("=" * 50)
    print("Testing imports...")
    print("=" * 50)

    try:
        from playwright_manager import PlaywrightManager
        print("✓ PlaywrightManager imported")
    except Exception as e:
        print(f"✗ PlaywrightManager import failed: {e}")
        return False

    try:
        from ops_web_base import WebCollectorBase, NoChangeError
        print("✓ WebCollectorBase imported")
    except Exception as e:
        print(f"✗ WebCollectorBase import failed: {e}")
        return False

    try:
        from ops_web import OperatorWeb
        print("✓ OperatorWeb imported")
    except Exception as e:
        print(f"✗ OperatorWeb import failed: {e}")
        return False

    print("\nAll imports successful!")
    return True


def test_web_collector_base():
    """Test WebCollectorBase functionality"""
    print("\n" + "=" * 50)
    print("Testing WebCollectorBase...")
    print("=" * 50)

    from ops_web_base import WebCollectorBase

    collector = WebCollectorBase()

    # Test configuration
    source = {
        "url": "https://example.com",
        "xpath": "//article",
        "browser_mode": False,
        "digest_splitting": False,
        "proxy": None,
    }
    collector.configure_from_source(source)

    assert collector.xpath == "//article"
    assert collector.browser_mode == False
    print("✓ Configuration works")

    # Test XPath extraction
    html = """
    <html>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>This is test content.</p>
            </article>
        </body>
    </html>
    """

    content = collector.xpath_extraction(html, "//article")
    assert "Test Article" in content
    assert "test content" in content
    print("✓ XPath extraction works")

    # Test URL cleaning
    url = "https://example.com/page?param=1#section"
    clean = collector.clean_url(url)
    assert clean == "https://example.com/page"
    print("✓ URL cleaning works")

    # Test URL extraction from HTML
    html_with_links = """
    <html>
        <body>
            <a href="/page1">Link 1</a>
            <a href="https://other.com/page2">Link 2</a>
        </body>
    </html>
    """
    urls = collector.get_urls_from_html("https://example.com", html_with_links)
    assert "https://example.com/page1" in urls
    assert "https://other.com/page2" in urls
    print("✓ URL extraction works")

    print("\nWebCollectorBase tests passed!")
    return True


def test_trafilatura():
    """Test Trafilatura content extraction"""
    print("\n" + "=" * 50)
    print("Testing Trafilatura extraction...")
    print("=" * 50)

    from trafilatura import extract

    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <article>
            <h1>Important News</h1>
            <p>This is the main content of the article. It contains important information
            that should be extracted by Trafilatura. The library is designed to extract
            the main content from web pages while ignoring navigation, ads, and other
            boilerplate content.</p>
            <p>Here is another paragraph with more details about the topic.</p>
        </article>
        <nav>Navigation links that should be ignored</nav>
        <footer>Footer content</footer>
    </body>
    </html>
    """

    content = extract(html)
    print(f"Extracted content:\n{content[:200]}...")

    assert content is not None
    assert "Important News" in content or "main content" in content
    print("✓ Trafilatura extraction works")

    return True


def test_fetch_real_page():
    """Test fetching a real web page (without browser mode)"""
    print("\n" + "=" * 50)
    print("Testing real page fetch...")
    print("=" * 50)

    from ops_web_base import WebCollectorBase

    collector = WebCollectorBase()

    # Fetch a simple page
    url = "https://httpbin.org/html"

    try:
        content, date = collector.fetch_article_content(url)
        print(f"Fetched {len(content)} bytes from {url}")
        assert len(content) > 0
        assert "Herman Melville" in content  # httpbin.org/html contains Moby Dick excerpt
        print("✓ Real page fetch works")
        return True
    except Exception as e:
        print(f"✗ Failed to fetch page: {e}")
        return False


def test_extract_web_content():
    """Test full content extraction pipeline"""
    print("\n" + "=" * 50)
    print("Testing web content extraction...")
    print("=" * 50)

    from ops_web_base import WebCollectorBase

    collector = WebCollectorBase()

    # Use a simple test page
    url = "https://httpbin.org/html"

    try:
        result = collector.extract_web_content(url)
        print(f"Extracted content: {len(result.get('content', ''))} chars")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Author: {result.get('author', 'N/A')}")

        assert result["content"] is not None
        print("✓ Content extraction works")
        return True
    except Exception as e:
        print(f"✗ Content extraction failed: {e}")
        return False


if __name__ == "__main__":
    results = []

    results.append(("Imports", test_imports()))
    results.append(("WebCollectorBase", test_web_collector_base()))
    results.append(("Trafilatura", test_trafilatura()))
    results.append(("Real page fetch", test_fetch_real_page()))
    results.append(("Content extraction", test_extract_web_content()))

    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
    sys.exit(0 if all_passed else 1)
