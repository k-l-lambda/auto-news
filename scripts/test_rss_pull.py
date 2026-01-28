#!/usr/bin/env python3
"""
Test RSS pull directly without going through the index database.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

import httpx
from notion_client import Client


def get_rss_sources():
    """Get RSS sources directly from RSS_LIST_DB_ID."""
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("RSS_LIST_DB_ID")

    if not db_id:
        print("[ERR] RSS_LIST_DB_ID not set in .env")
        return []

    notion = Client(auth=token)

    # Query database for enabled RSS sources
    query_data = {
        "database_id": db_id,
        "filter": {
            "property": "Enabled",
            "checkbox": {"equals": True}
        }
    }

    results = notion.databases.query(**query_data).get("results", [])
    sources = []

    for page in results:
        props = page["properties"]
        name = ""
        if props.get("Name", {}).get("title"):
            name = props["Name"]["title"][0]["text"]["content"]

        url = props.get("URL", {}).get("url", "")
        if name and url:
            sources.append({"name": name, "url": url})

    return sources


def fetch_rss_feed(url: str, limit: int = 3):
    """Fetch RSS feed and return articles."""
    import feedparser

    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:limit]:
        article = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")[:200] if entry.get("summary") else ""
        }
        articles.append(article)

    return articles


def main():
    print("=== RSS Pull Test ===\n")

    # Get RSS sources from Notion
    print("[1] Fetching RSS sources from Notion...")
    sources = get_rss_sources()
    print(f"    Found {len(sources)} enabled sources\n")

    if not sources:
        print("[ERR] No RSS sources found")
        return

    # Test fetch from first 3 sources
    test_sources = sources[:3]
    print(f"[2] Testing fetch from {len(test_sources)} sources...\n")

    for source in test_sources:
        print(f"  [{source['name']}]")
        print(f"    URL: {source['url']}")

        try:
            articles = fetch_rss_feed(source['url'], limit=2)
            print(f"    Articles: {len(articles)}")
            for art in articles:
                print(f"      - {art['title'][:60]}...")
        except Exception as e:
            print(f"    [ERR] {e}")
        print()

    print("[OK] RSS pull test complete!")


if __name__ == "__main__":
    main()
