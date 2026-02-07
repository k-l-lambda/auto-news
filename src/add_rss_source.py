#!/usr/bin/env python3
"""
Add RSS source to Notion database.

Usage:
    python add_rss_source.py --name "arXiv Astrophysics" --url "https://rss.arxiv.org/rss/astro-ph"
    python add_rss_source.py --list  # List all RSS sources
"""
import os
import argparse
from dotenv import load_dotenv
from notion import NotionAgent


def get_rss_database_id():
    """Get the RSS list database ID from environment or Notion index"""
    # First try to get from environment variable
    rss_db_id = os.getenv("RSS_LIST_DB_ID")
    if rss_db_id:
        print(f"Using RSS_LIST_DB_ID from environment: {rss_db_id}")
        return rss_db_id

    # Fallback: try to get from Notion index
    from ops_notion import OperatorNotion
    import utils

    notion_api_key = os.getenv("NOTION_TOKEN")
    notion_agent = NotionAgent(notion_api_key)
    op_notion = OperatorNotion()

    db_index_id = op_notion.get_index_inbox_dbid()
    print(f"Index inbox database ID: {db_index_id}")

    db_pages = utils.get_notion_database_pages_inbox(
        notion_agent, db_index_id, "RSS")

    if not db_pages:
        print("No RSS database found in index")
        return None

    # Get the latest RSS database
    return db_pages[0]["database_id"]


def list_rss_sources():
    """List all RSS sources in the database"""
    notion_api_key = os.getenv("NOTION_TOKEN")
    notion_agent = NotionAgent(notion_api_key)

    database_id = get_rss_database_id()
    if not database_id:
        return

    print(f"\nRSS Database ID: {database_id}")
    print("-" * 60)

    rss_list = notion_agent.queryDatabase_RSSList(database_id)

    print(f"\nFound {len(rss_list)} RSS sources:\n")
    for rss in rss_list:
        name = rss.get("name", "")
        url = rss.get("url", "")
        print(f"  - {name}")
        print(f"    URL: {url}")
        print()


def add_rss_source(name: str, url: str, enabled: bool = True):
    """Add a new RSS source to the Notion database"""
    notion_api_key = os.getenv("NOTION_TOKEN")
    notion_agent = NotionAgent(notion_api_key)

    database_id = get_rss_database_id()
    if not database_id:
        print("Cannot find RSS database")
        return False

    print(f"Adding RSS source to database: {database_id}")
    print(f"  Name: {name}")
    print(f"  URL: {url}")
    print(f"  Enabled: {enabled}")

    # Create the database item
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": name
                    }
                }
            ]
        },
        "URL": {
            "url": url
        },
        "Enabled": {
            "checkbox": enabled
        }
    }

    try:
        result = notion_agent.api.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        print(f"\nSuccess! Created page: {result['id']}")
        print(f"URL: {result['url']}")
        return True
    except Exception as e:
        print(f"Error creating RSS source: {e}")
        return False


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Add RSS source to Notion")
    parser.add_argument("--name", help="Name of the RSS source")
    parser.add_argument("--url", help="URL of the RSS feed")
    parser.add_argument("--list", action="store_true", help="List all RSS sources")
    parser.add_argument("--disabled", action="store_true", help="Add as disabled")

    args = parser.parse_args()

    if args.list:
        list_rss_sources()
    elif args.name and args.url:
        add_rss_source(args.name, args.url, enabled=not args.disabled)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
