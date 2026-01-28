#!/usr/bin/env python3
"""
Add RSS sources to Notion RSS_List database.

Usage:
    python scripts/add_rss_source.py --name "HackerNews" --url "https://hnrss.org/frontpage"
    python scripts/add_rss_source.py --list  # List all RSS sources
    python scripts/add_rss_source.py --batch sources.json  # Batch add from JSON
"""

import argparse
import json
import os
import sys
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


def get_headers():
    """Get Notion API headers."""
    token = os.getenv("NOTION_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }


def get_rss_list_db_id(entry_page_id: str) -> str:
    """Find RSS_List database ID from entry page."""
    # First check env var for cached ID
    cached_id = os.getenv("RSS_LIST_DB_ID")
    if cached_id:
        return cached_id

    headers = get_headers()

    # Get children of entry page
    try:
        with httpx.Client() as client:
            response = client.get(
                f"https://api.notion.com/v1/blocks/{entry_page_id}/children",
                headers=headers,
                timeout=30.0
            )
        children = response.json().get("results", [])
        for child in children:
            if child.get("type") == "child_database":
                db_id = child.get("id")
                # Get database info
                try:
                    with httpx.Client() as client:
                        response = client.get(
                            f"https://api.notion.com/v1/databases/{db_id}",
                            headers=headers,
                            timeout=30.0
                        )
                    db_info = response.json()
                    title = "".join([t.get("plain_text", "") for t in db_info.get("title", [])])
                    if "RSS" in title and "List" in title:
                        return db_id
                except:
                    continue
    except Exception as e:
        print(f"Warning: Could not search entry page children: {e}")

    return None


def list_rss_sources(db_id: str):
    """List all RSS sources in the database."""
    headers = get_headers()

    with httpx.Client() as client:
        response = client.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers,
            json={},
            timeout=30.0
        )
    results = response.json().get("results", [])

    print(f"\n{'='*60}")
    print(f"RSS Sources ({len(results)} total)")
    print(f"{'='*60}\n")

    for page in results:
        props = page["properties"]

        name = ""
        if props.get("Name", {}).get("title"):
            name = props["Name"]["title"][0]["text"]["content"]

        url = props.get("URL", {}).get("url", "")
        enabled = props.get("Enabled", {}).get("checkbox", False)

        status = "[ON]" if enabled else "[OFF]"
        print(f"{status} {name}")
        print(f"      URL: {url}")
        print()


def add_rss_source(db_id: str, name: str, url: str,
                   enabled: bool = True, xpath: str = "",
                   browser_mode: bool = False, fetch_full: bool = False):
    """Add a new RSS source to the database."""
    headers = get_headers()

    properties = {
        "Name": {
            "title": [{"text": {"content": name}}]
        },
        "URL": {
            "url": url
        },
        "Enabled": {
            "checkbox": enabled
        }
    }

    # Add optional enhanced fields if provided
    if xpath:
        properties["XPath"] = {
            "rich_text": [{"text": {"content": xpath}}]
        }

    if browser_mode:
        properties["Browser Mode"] = {
            "checkbox": True
        }

    if fetch_full:
        properties["Fetch Full Article"] = {
            "checkbox": True
        }

    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json={
                    "parent": {"database_id": db_id},
                    "properties": properties
                },
                timeout=30.0
            )

        if response.status_code == 200:
            print(f"[OK] Added: {name}")
            print(f"     URL: {url}")
            return True
        else:
            print(f"[ERR] Failed to add {name}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"[ERR] Failed to add {name}: {e}")
        return False


def batch_add(db_id: str, json_file: str):
    """Batch add RSS sources from JSON file."""
    with open(json_file, 'r') as f:
        sources = json.load(f)

    success = 0
    for source in sources:
        if add_rss_source(
            db_id,
            name=source["name"],
            url=source["url"],
            enabled=source.get("enabled", True),
            xpath=source.get("xpath", ""),
            browser_mode=source.get("browser_mode", False),
            fetch_full=source.get("fetch_full_article", False)
        ):
            success += 1

    print(f"\n[OK] Added {success}/{len(sources)} sources")


# Predefined popular RSS sources
POPULAR_SOURCES = [
    {"name": "Hacker News - Front Page", "url": "https://hnrss.org/frontpage"},
    {"name": "Hacker News - Best", "url": "https://hnrss.org/best"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss/"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/"},
    {"name": "Simon Willison's Blog", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Stratechery", "url": "https://stratechery.com/feed/"},
    {"name": "Benedict Evans", "url": "https://www.ben-evans.com/benedictevans?format=rss"},
]

# Chinese tech sources
CHINESE_SOURCES = [
    {"name": "36Kr", "url": "https://36kr.com/feed"},
    {"name": "InfoQ CN", "url": "https://www.infoq.cn/feed"},
    {"name": "Solidot", "url": "https://www.solidot.org/index.rss"},
    {"name": "V2EX", "url": "https://www.v2ex.com/index.xml"},
    {"name": "Ruby China", "url": "https://ruby-china.org/topics/feed"},
    {"name": "CoolShell (archived)", "url": "https://coolshell.cn/feed"},
]


def main():
    parser = argparse.ArgumentParser(description="Manage RSS sources in Notion")
    parser.add_argument("--name", help="RSS source name")
    parser.add_argument("--url", help="RSS feed URL")
    parser.add_argument("--list", action="store_true", help="List all RSS sources")
    parser.add_argument("--batch", help="Batch add from JSON file")
    parser.add_argument("--add-popular", action="store_true", help="Add popular tech RSS sources")
    parser.add_argument("--add-chinese", action="store_true", help="Add Chinese tech RSS sources")
    parser.add_argument("--xpath", default="", help="XPath for content extraction")
    parser.add_argument("--browser-mode", action="store_true", help="Enable browser mode")
    parser.add_argument("--fetch-full", action="store_true", help="Fetch full article content")
    parser.add_argument("--disabled", action="store_true", help="Add as disabled")

    args = parser.parse_args()

    # Check required env vars
    token = os.getenv("NOTION_TOKEN")
    entry_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    if not token or not entry_page_id:
        print("[ERR] NOTION_TOKEN and NOTION_ENTRY_PAGE_ID must be set in .env")
        sys.exit(1)

    # Find RSS_List database
    db_id = get_rss_list_db_id(entry_page_id)

    if not db_id:
        print("[ERR] RSS_List database not found in Notion")
        print("      Please run: python scripts/populate_rss_sources.py")
        print("      Or set RSS_LIST_DB_ID in .env")
        sys.exit(1)

    print(f"[OK] Found RSS_List database: {db_id[:8]}...")

    # Execute command
    if args.list:
        list_rss_sources(db_id)

    elif args.batch:
        batch_add(db_id, args.batch)

    elif args.add_popular:
        print("\n[INFO] Adding popular tech RSS sources...")
        for source in POPULAR_SOURCES:
            add_rss_source(db_id, source["name"], source["url"])

    elif args.add_chinese:
        print("\n[INFO] Adding Chinese tech RSS sources...")
        for source in CHINESE_SOURCES:
            add_rss_source(db_id, source["name"], source["url"])

    elif args.name and args.url:
        add_rss_source(
            db_id,
            name=args.name,
            url=args.url,
            enabled=not args.disabled,
            xpath=args.xpath,
            browser_mode=args.browser_mode,
            fetch_full=args.fetch_full
        )

    else:
        parser.print_help()
        print("\nExamples:")
        print('  python scripts/add_rss_source.py --name "HackerNews" --url "https://hnrss.org/frontpage"')
        print('  python scripts/add_rss_source.py --list')
        print('  python scripts/add_rss_source.py --add-popular')
        print('  python scripts/add_rss_source.py --add-chinese')


if __name__ == "__main__":
    main()
