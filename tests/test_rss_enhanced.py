#!/usr/bin/env python3
"""
Test enhanced RSS collector functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


def test_imports():
    """Test that OperatorRSS inherits from WebCollectorBase"""
    print("=" * 50)
    print("Testing imports...")
    print("=" * 50)

    from ops_rss import OperatorRSS
    from ops_web_base import WebCollectorBase

    op = OperatorRSS()

    # Check inheritance
    assert isinstance(op, WebCollectorBase), "OperatorRSS should inherit from WebCollectorBase"
    print("✓ OperatorRSS inherits from WebCollectorBase")

    # Check web collector methods are available
    assert hasattr(op, 'fetch_article_content')
    assert hasattr(op, 'extract_web_content')
    assert hasattr(op, 'xpath_extraction')
    assert hasattr(op, 'configure_from_source')
    print("✓ Web collector methods available")

    return True


def test_fetch_basic_rss():
    """Test basic RSS fetching without enhanced features"""
    print("\n" + "=" * 50)
    print("Testing basic RSS fetch...")
    print("=" * 50)

    from ops_rss import OperatorRSS

    op = OperatorRSS()

    # Use a reliable test RSS feed
    feed_url = "https://hnrss.org/newest?count=3"
    list_name = "HackerNews"

    articles = op._fetch_articles(list_name, feed_url, count=2)

    print(f"Fetched {len(articles)} articles")
    assert len(articles) > 0, "Should fetch at least one article"

    article = articles[0]
    assert "title" in article
    assert "url" in article
    assert "source" in article
    assert article["source"] == "RSS"
    print(f"✓ First article: {article['title'][:50]}...")

    return True


def test_fetch_with_full_article():
    """Test RSS fetching with full article extraction"""
    print("\n" + "=" * 50)
    print("Testing RSS with full article extraction...")
    print("=" * 50)

    from ops_rss import OperatorRSS

    op = OperatorRSS()

    # Use a feed where we can test full article fetch
    feed_url = "https://hnrss.org/newest?count=2"
    list_name = "HackerNews-Full"

    rss_config = {
        "browser_mode": False,
        "xpath": "",
        "fetch_full_article": True,
        "proxy": "",
    }

    articles = op._fetch_articles(list_name, feed_url, count=1, rss_config=rss_config)

    print(f"Fetched {len(articles)} articles with full content")
    assert len(articles) > 0, "Should fetch at least one article"

    article = articles[0]
    print(f"Title: {article['title'][:50]}...")
    print(f"Content length: {len(article.get('content', ''))} chars")

    # Note: content might be empty if the linked page is JS-heavy
    # or blocks scraping, so we don't assert on content length
    print("✓ Full article fetch completed")

    return True


def test_notion_rss_query():
    """Test that Notion RSS query includes enhanced fields"""
    print("\n" + "=" * 50)
    print("Testing Notion RSS query structure...")
    print("=" * 50)

    from notion import NotionAgent

    # Mock test - just verify the method exists and has right signature
    agent = NotionAgent.__new__(NotionAgent)

    # Check method signature includes enhanced fields handling
    import inspect
    source = inspect.getsource(NotionAgent.queryDatabase_RSSList)

    assert "xpath" in source.lower(), "Should handle xpath field"
    assert "browser_mode" in source.lower() or "browser mode" in source.lower(), "Should handle browser_mode field"
    assert "fetch_full_article" in source.lower() or "fetch full article" in source.lower(), "Should handle fetch_full_article field"
    print("✓ Notion query includes enhanced fields")

    return True


if __name__ == "__main__":
    results = []

    results.append(("Imports", test_imports()))
    results.append(("Basic RSS fetch", test_fetch_basic_rss()))
    results.append(("Full article fetch", test_fetch_with_full_article()))
    results.append(("Notion query structure", test_notion_rss_query()))

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
