#!/usr/bin/env python3
"""Test full RSS pipeline with all services"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

# Load API keys
other_mcp_env = os.path.expanduser("~/work/other-mcp/.env")
if os.path.exists(other_mcp_env):
    load_dotenv(other_mcp_env)
    if os.getenv("SUBAGENT_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("SUBAGENT_API_KEY")
    if os.getenv("SUBAGENT_BASE_URL") and not os.getenv("OPENAI_API_BASE"):
        os.environ["OPENAI_API_BASE"] = os.getenv("SUBAGENT_BASE_URL")

load_dotenv()

from ops_rss import OperatorRSS


def main():
    print("="*60)
    print("Full RSS Pipeline Test")
    print("="*60)

    op = OperatorRSS()

    # Step 1: Fetch RSS articles directly (bypass Notion inbox)
    print("\n📡 Step 1: Fetching RSS articles...")
    test_feeds = [
        ("HackerNews", "https://hnrss.org/frontpage"),
    ]

    pages = {}
    for feed_name, feed_url in test_feeds:
        articles = op._fetch_articles(feed_name, feed_url, count=3)
        for article in articles:
            pages[article["id"]] = article
            print(f"   ✓ {article['title'][:50]}...")

    print(f"\n   Total: {len(pages)} articles")

    # Step 2: Summarize
    print("\n🤖 Step 2: Summarizing articles...")
    pages_list = list(pages.values())
    summarized = op.summarize(pages_list)
    print(f"   Summarized: {len(summarized)} articles")

    # Step 3: Rank (classification)
    print("\n📊 Step 3: Ranking articles...")
    ranked = op.rank(summarized)
    print(f"   Ranked: {len(ranked)} articles")

    # Step 4: Push to Notion (simplified method)
    print("\n📤 Step 4: Pushing to Notion...")

    from notion import NotionAgent
    notion_agent = NotionAgent()

    # Get ToRead page and create a simple database
    from mysql_cli import MySQLClient
    db_cli = MySQLClient()
    indexes = db_cli.index_pages_table_load()
    toread_page_id = indexes["notion"]["toread_page_id"]["index_id"]

    from datetime import datetime

    # Create a minimal database with only Name property
    title = [{
        "type": "text",
        "text": {"content": f"RSS - {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
    }]
    db = notion_agent.api.databases.create(
        parent={"type": "page_id", "page_id": toread_page_id},
        title=title,
        properties={"Name": {"title": {}}}
    )
    database_id = db["id"]
    print(f"   Created database: {database_id}")

    pushed = 0
    for article in ranked[:3]:
        try:
            # Create page with Name only, content in blocks
            properties = {
                "Name": {"title": [{"text": {"content": f"[{article.get('list_name', 'RSS')}] {article['title'][:80]}"}}]}
            }

            summary = article.get("__summary", "No summary")
            url = article.get("url", "")

            blocks = [
                {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": f"🔗 {url}"}}]}},
                {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": f"\n📝 Summary:\n{summary[:1900]}"}}]}},
            ]

            notion_agent.api.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=blocks
            )
            pushed += 1
            print(f"   ✓ {article['title'][:40]}...")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    print(f"   Total pushed: {pushed}")

    print("\n" + "="*60)
    print("✅ Pipeline completed!")
    print("="*60)


if __name__ == "__main__":
    main()
