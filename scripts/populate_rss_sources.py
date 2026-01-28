#!/usr/bin/env python3
"""
Populate RSS sources into the working database.
"""

import os
import sys
import json
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


RSS_SOURCES = [
    # General Tech News
    {"name": "Hacker News - Front Page", "url": "https://hnrss.org/frontpage"},
    {"name": "Hacker News - Best", "url": "https://hnrss.org/best"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},

    # AI/ML Blogs
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss/"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/"},

    # Developer Blogs
    {"name": "Simon Willison's Blog", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Stratechery", "url": "https://stratechery.com/feed/"},
    {"name": "Benedict Evans", "url": "https://www.ben-evans.com/benedictevans?format=rss"},

    # Chinese Tech (Optional - uncomment if needed)
    {"name": "36Kr", "url": "https://36kr.com/feed"},
    {"name": "InfoQ CN", "url": "https://www.infoq.cn/feed"},
    {"name": "Solidot", "url": "https://www.solidot.org/index.rss"},
]


def main():
    token = os.getenv("NOTION_TOKEN")
    entry_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # First create a proper RSS_List database
    print("📋 Creating RSS_List database...")

    db_payload = {
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
            json=db_payload,
            timeout=30.0
        )

    if response.status_code != 200:
        print(f"❌ Failed to create database: {response.text}")
        return

    result = response.json()
    db_id = result.get("id")
    props = list(result.get("properties", {}).keys())
    print(f"✅ Created database: {db_id[:8]}...")
    print(f"   Properties: {props}")

    # Now add all RSS sources
    print(f"\n📰 Adding {len(RSS_SOURCES)} RSS sources...")

    success = 0
    with httpx.Client() as client:
        for source in RSS_SOURCES:
            page_payload = {
                "parent": {"database_id": db_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": source["name"]}}]},
                    "URL": {"url": source["url"]},
                    "Enabled": {"checkbox": True}
                }
            }

            response = client.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=page_payload,
                timeout=30.0
            )

            if response.status_code == 200:
                print(f"  ✅ {source['name']}")
                success += 1
            else:
                print(f"  ❌ {source['name']}: {response.text[:100]}")

    print(f"\n✅ Added {success}/{len(RSS_SOURCES)} RSS sources")
    print(f"\n📋 Database ID: {db_id}")
    print(f"   Add this to your .env as RSS_LIST_DB_ID={db_id}")


if __name__ == "__main__":
    main()
