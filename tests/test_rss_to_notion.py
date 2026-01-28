#!/usr/bin/env python3
"""
Simplified RSS to Notion test - bypasses MySQL dependency
Fetches RSS feeds and pushes directly to Notion
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

# Load env from other-mcp for LLM API
other_mcp_env = os.path.expanduser("~/work/other-mcp/.env")
if os.path.exists(other_mcp_env):
    load_dotenv(other_mcp_env)
    if os.getenv("SUBAGENT_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("SUBAGENT_API_KEY")
    if os.getenv("SUBAGENT_BASE_URL") and not os.getenv("OPENAI_API_BASE"):
        os.environ["OPENAI_API_BASE"] = os.getenv("SUBAGENT_BASE_URL")

load_dotenv()

import feedparser
from notion import NotionAgent
from llm_agent import LLMAgentSummary
import utils


def fetch_rss_articles(feed_url, feed_name, count=3):
    """Fetch articles from RSS feed"""
    print(f"\n📡 Fetching RSS: {feed_name}")
    print(f"   URL: {feed_url}")

    feed = feedparser.parse(feed_url)
    articles = []

    for i, entry in enumerate(feed.entries[:count]):
        article = {
            "title": entry.title,
            "url": entry.link,
            "summary": entry.get("summary", "")[:500],
            "published": entry.get("published", ""),
            "feed_name": feed_name,
        }
        articles.append(article)
        print(f"   [{i+1}] {article['title'][:50]}...")

    return articles


def summarize_article(agent, article):
    """Generate summary using LLM"""
    content = f"{article['title']}\n\n{article['summary']}"
    if len(content) < 50:
        return article['summary']

    try:
        summary = agent.run(content)
        return summary
    except Exception as e:
        print(f"   ⚠ Summary failed: {e}")
        return article['summary']


def create_toread_database(notion_agent, parent_page_id):
    """Create a simple database under the parent page"""
    print("\n📊 Creating ToRead database...")

    # Create a minimal database with only Name property
    title = [{
        "type": "text",
        "text": {"content": f"ToRead - {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
    }]

    properties = {
        "Name": {"title": {}},
    }

    db = notion_agent.api.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=title,
        properties=properties
    )

    print(f"   ✓ Created database: {db['id']}")
    return db['id']


def push_to_notion(notion_agent, database_id, article, summary):
    """Push article to Notion database"""
    print(f"   📤 Pushing: {article['title'][:40]}...")

    # Only use Name (title) property
    properties = {
        "Name": {
            "title": [{
                "text": {"content": f"[{article['feed_name']}] {article['title'][:80]}"}
            }]
        },
    }

    # Content blocks
    blocks = []

    # Add source info
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "text": {"content": f"🔗 Source: {article['url']}"}
            }]
        }
    })

    # Add summary
    summary_text = summary[:1900] if summary else "No summary available"
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "text": {"content": f"\n📝 Summary:\n{summary_text}"}
            }]
        }
    })

    new_page = notion_agent.api.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=blocks
    )

    return new_page


def main():
    print("="*60)
    print("🚀 RSS to Notion Test")
    print("="*60)

    # Check config
    token = os.getenv("NOTION_TOKEN")
    page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    if not token or not page_id:
        print("❌ ERROR: NOTION_TOKEN or NOTION_ENTRY_PAGE_ID not set")
        return

    print(f"✓ Notion Token: {token[:10]}...")
    print(f"✓ Entry Page ID: {page_id}")

    # Initialize agents
    print("\n🔧 Initializing agents...")
    notion_agent = NotionAgent(token)

    llm_agent = LLMAgentSummary()
    llm_agent.init_prompt(translation_enabled=False)
    llm_agent.init_llm()
    print("   ✓ Notion Agent ready")
    print("   ✓ LLM Agent ready")

    # Create database
    database_id = create_toread_database(notion_agent, page_id)

    # RSS feeds to fetch
    feeds = [
        ("HackerNews", "https://hnrss.org/frontpage"),
        # ("TechCrunch", "https://techcrunch.com/feed/"),
    ]

    # Fetch and process
    total_pushed = 0

    for feed_name, feed_url in feeds:
        articles = fetch_rss_articles(feed_url, feed_name, count=3)

        print(f"\n🤖 Processing {len(articles)} articles with LLM...")

        for article in articles:
            try:
                # Generate summary
                summary = summarize_article(llm_agent, article)

                # Push to Notion
                push_to_notion(notion_agent, database_id, article, summary)
                total_pushed += 1

            except Exception as e:
                print(f"   ❌ Error processing {article['title'][:30]}: {e}")

    print("\n" + "="*60)
    print(f"✅ Done! Pushed {total_pushed} articles to Notion")
    print(f"📖 View in Notion: https://notion.so/{page_id}")
    print("="*60)


if __name__ == "__main__":
    main()
