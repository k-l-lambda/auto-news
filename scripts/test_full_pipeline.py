#!/usr/bin/env python3
"""
Test full pipeline: RSS -> LLM Summary -> LLM Ranking
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

import feedparser
from notion_client import Client


def get_rss_sources(limit=2):
    """Get RSS sources from Notion."""
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("RSS_LIST_DB_ID")
    notion = Client(auth=token)

    results = notion.databases.query(
        database_id=db_id,
        filter={"property": "Enabled", "checkbox": {"equals": True}}
    ).get("results", [])

    sources = []
    for page in results[:limit]:
        props = page["properties"]
        name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "")
        url = props.get("URL", {}).get("url", "")
        if name and url:
            sources.append({"name": name, "url": url})
    return sources


def fetch_article(url: str):
    """Fetch article content."""
    feed = feedparser.parse(url)
    if feed.entries:
        entry = feed.entries[0]
        return {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "content": entry.get("summary", "") or entry.get("description", "")
        }
    return None


def test_llm_summary(text: str):
    """Test LLM summarization."""
    from llm_agent import LLMAgentSummary

    agent = LLMAgentSummary()
    agent.init_prompt()
    agent.init_llm()

    summary = agent.run(text)
    return summary


def test_llm_ranking(text: str):
    """Test LLM ranking."""
    from llm_agent import LLMAgentCategoryAndRanking

    agent = LLMAgentCategoryAndRanking()
    agent.init_prompt()
    agent.init_llm()

    result = agent.run(text)
    return result


def main():
    print("=" * 60)
    print("Full Pipeline Test: RSS -> LLM Summary -> LLM Ranking")
    print("=" * 60)

    # Step 1: Get RSS sources
    print("\n[1] Getting RSS sources from Notion...")
    sources = get_rss_sources(limit=1)
    if not sources:
        print("    [ERR] No sources found")
        return

    source = sources[0]
    print(f"    Source: {source['name']}")
    print(f"    URL: {source['url']}")

    # Step 2: Fetch article
    print("\n[2] Fetching article...")
    article = fetch_article(source['url'])
    if not article:
        print("    [ERR] No article found")
        return

    print(f"    Title: {article['title'][:60]}...")
    print(f"    Content length: {len(article['content'])} chars")

    # Step 3: LLM Summary
    print("\n[3] Generating LLM Summary...")
    if len(article['content']) < 100:
        print("    [SKIP] Content too short for summary")
        summary = article['content']
    else:
        try:
            summary = test_llm_summary(article['content'])
            print(f"    Summary: {summary[:200]}...")
        except Exception as e:
            print(f"    [ERR] Summary failed: {e}")
            summary = article['content'][:500]

    # Step 4: LLM Ranking
    print("\n[4] Generating LLM Ranking...")
    try:
        text_for_ranking = f"Title: {article['title']}\n\nContent: {summary}"
        ranking = test_llm_ranking(text_for_ranking)
        print(f"    Ranking result: {ranking[:300]}...")
    except Exception as e:
        print(f"    [ERR] Ranking failed: {e}")

    print("\n" + "=" * 60)
    print("[OK] Pipeline test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
