#!/usr/bin/env python3
"""
Initialize RSS_List database in Notion.
"""

import os
import sys
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


def create_rss_list_database(entry_page_id: str, token: str) -> str:
    """Create RSS_List database with all necessary columns."""

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": {"type": "page_id", "page_id": entry_page_id},
        "title": [{"type": "text", "text": {"content": "RSS_List"}}],
        "properties": {
            "Name": {"title": {}},
            "URL": {"url": {}},
            "Enabled": {"checkbox": {}},
            "XPath": {"rich_text": {}},
            "Browser Mode": {"checkbox": {}},
            "Fetch Full Article": {"checkbox": {}},
            "Proxy": {"rich_text": {}},
            "Notes": {"rich_text": {}}
        }
    }

    with httpx.Client() as client:
        response = client.post(
            "https://api.notion.com/v1/databases",
            headers=headers,
            json=payload,
            timeout=30.0
        )

    if response.status_code != 200:
        raise Exception(f"Failed to create database: {response.text}")

    result = response.json()
    return result["id"]


def main():
    token = os.getenv("NOTION_TOKEN")
    entry_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    if not token or not entry_page_id:
        print("[ERR] NOTION_TOKEN and NOTION_ENTRY_PAGE_ID must be set")
        sys.exit(1)

    print("[INFO] Creating RSS_List database...")

    try:
        db_id = create_rss_list_database(entry_page_id, token)
        print(f"[OK] Created RSS_List database: {db_id}")
        print("\nDatabase columns:")
        print("  - Name (title) - RSS source name")
        print("  - URL (url) - RSS feed URL")
        print("  - Enabled (checkbox) - Enable/disable toggle")
        print("  - XPath (text) - Optional content extraction path")
        print("  - Browser Mode (checkbox) - Enable Playwright rendering")
        print("  - Fetch Full Article (checkbox) - Use Trafilatura extraction")
        print("  - Proxy (text) - Optional proxy URL")
        print("  - Notes (text) - Notes about the source")
        print(f"\nAdd this to your .env:")
        print(f"  RSS_LIST_DB_ID={db_id}")
        print("\nYou can now add RSS sources using:")
        print('  python scripts/add_rss_source.py --name "HackerNews" --url "https://hnrss.org/frontpage"')
    except Exception as e:
        print(f"[ERR] Failed to create database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
