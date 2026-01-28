#!/usr/bin/env python3
"""Push formatted content to Notion with User Rating - using direct API"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

import httpx

TOKEN = os.getenv("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


def api_post(endpoint, data):
    """POST to Notion API"""
    url = f"https://api.notion.com/v1{endpoint}"
    response = httpx.post(url, headers=HEADERS, json=data, timeout=30)
    result = response.json()
    if response.status_code != 200:
        print(f"API Error: {result}")
    return result


def api_get(endpoint):
    """GET from Notion API"""
    url = f"https://api.notion.com/v1{endpoint}"
    response = httpx.get(url, headers=HEADERS, timeout=30)
    return response.json()


def create_database(parent_page_id, name):
    """Create database with User Rating and other properties"""
    print(f"\n📊 Creating database: {name}")

    data = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": name}}],
        "properties": {
            "Name": {"title": {}},
            "Source": {
                "select": {
                    "options": [
                        {"name": "RSS", "color": "blue"},
                        {"name": "Web", "color": "green"},
                    ]
                }
            },
            "Score": {"number": {}},
            "User Rating": {
                "select": {
                    "options": [
                        {"name": "⭐", "color": "gray"},
                        {"name": "⭐⭐", "color": "yellow"},
                        {"name": "⭐⭐⭐", "color": "orange"},
                        {"name": "⭐⭐⭐⭐", "color": "green"},
                        {"name": "⭐⭐⭐⭐⭐", "color": "blue"},
                    ]
                }
            },
            "Tags": {"multi_select": {}},
            "Link": {"url": {}},
            "Read": {"checkbox": {}},
        }
    }

    result = api_post("/databases", data)

    if "id" in result:
        print(f"   ✓ Database created: {result['id']}")
        # Verify properties
        db_info = api_get(f"/databases/{result['id']}")
        print(f"   Properties: {list(db_info.get('properties', {}).keys())}")
        return result["id"]
    else:
        print(f"   ✗ Failed: {result}")
        return None


def push_article(database_id, article):
    """Push article with formatted content"""
    print(f"\n   📤 Pushing: {article['title'][:40]}...")

    # Build properties
    properties = {
        "Name": {"title": [{"text": {"content": article["title"]}}]},
        "Source": {"select": {"name": article.get("source", "RSS")}},
        "Score": {"number": article.get("score", 0.5)},
        "Tags": {"multi_select": [{"name": t} for t in article.get("tags", [])]},
        "Link": {"url": article.get("url")},
        "Read": {"checkbox": False},
    }

    # Build formatted blocks
    blocks = []

    # Header
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "📰 Summary"}}]
        }
    })

    # Link
    blocks.append({
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": article.get("url", "")}
    })

    # Divider
    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # Summary points as bullet list
    summary_lines = article.get("summary", "").strip().split("\n")
    for line in summary_lines:
        line = line.strip()
        if not line:
            continue

        # Remove leading numbers like "1. " or "- "
        if line[0].isdigit() and "." in line[:3]:
            line = line[line.find(".")+1:].strip()
        elif line.startswith("- "):
            line = line[2:]

        # Check for bold markers
        if "**" in line:
            # Split by ** to create bold sections
            parts = line.split("**")
            rich_text = []
            for i, part in enumerate(parts):
                if part:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part},
                        "annotations": {"bold": i % 2 == 1}  # Odd indices were between **
                    })

            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text}
            })
        else:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })

    # Callout for insight
    if article.get("insight"):
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": article["insight"]}}],
                "icon": {"emoji": "💡"}
            }
        })

    # Code block
    if article.get("code"):
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": article["code"]}}],
                "language": article.get("code_lang", "typescript")
            }
        })

    # Quote reminder
    blocks.append({
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": [
                {"type": "text", "text": {"content": "👆 Please rate this article using "}, "annotations": {"italic": True}},
                {"type": "text", "text": {"content": "User Rating"}, "annotations": {"bold": True, "italic": True}},
                {"type": "text", "text": {"content": " property above!"}, "annotations": {"italic": True}},
            ]
        }
    })

    # Create page
    data = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": blocks
    }

    result = api_post("/pages", data)

    if "id" in result:
        print(f"      ✓ Created: {result['url']}")
        return result
    else:
        print(f"      ✗ Error: {result.get('message', result)}")
        return None


def main():
    print("="*60)
    print("Formatted Push with User Rating")
    print("="*60)

    # Get ToRead page ID from MySQL
    from mysql_cli import MySQLClient
    db_cli = MySQLClient()
    indexes = db_cli.index_pages_table_load()
    toread_page_id = indexes["notion"]["toread_page_id"]["index_id"]

    # Create database
    db_name = f"ToRead - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    database_id = create_database(toread_page_id, db_name)

    if not database_id:
        print("Failed to create database!")
        return

    # Test articles
    articles = [
        {
            "title": "Make.ts - TypeScript Build Scripts",
            "url": "https://matklad.github.io/2026/01/27/make-ts.html",
            "source": "RSS",
            "score": 0.85,
            "tags": ["TypeScript", "DevTools"],
            "summary": """1. **Workflow pattern**: Replace ad-hoc shell commands with a single make.ts file
2. **Benefits**: Better ergonomics, editor support, fewer && chains
3. **Tooling**: TypeScript + Deno + dax library for subprocess handling
4. **Example**: TigerBeetle benchmark script that manages cluster lifecycle""",
            "insight": "Interactive scripting with TypeScript provides better developer experience than Makefiles",
            "code": """// make.ts
import $ from "dax";
await $\`tsc --build\`;
await $\`node dist/main.js\`;""",
            "code_lang": "typescript"
        },
        {
            "title": "I Stopped Following the News",
            "url": "https://mertbulan.com/2026/01/28/why-i-stopped-following-the-news/",
            "source": "RSS",
            "score": 0.72,
            "tags": ["Productivity", "Wellbeing"],
            "summary": """1. Daily news increased **stress** without useful information
2. Replaced with **meaningful reading** - books and quality magazines
3. Local updates via short **newsletter** are sufficient
4. Result: More books read, better **mental state**""",
            "insight": "News optimizes for engagement, not for informing you about things that matter",
        },
    ]

    print("\n📤 Pushing articles...")
    for article in articles:
        push_article(database_id, article)

    print("\n" + "="*60)
    print("✅ Done! Go to Notion and:")
    print("   1. View the formatted articles")
    print("   2. Set a User Rating (⭐ to ⭐⭐⭐⭐⭐)")
    print("   3. Add a comment")
    print("="*60)


if __name__ == "__main__":
    main()
