#!/usr/bin/env python3
"""Initialize Notion database structure"""

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

from ops_notion import OperatorNotion


def main():
    print("="*60)
    print("Initializing Notion Database Structure")
    print("="*60)

    token = os.getenv("NOTION_TOKEN")
    page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    print(f"Token: {token[:15]}...")
    print(f"Entry Page ID: {page_id}")
    print()

    op_notion = OperatorNotion()

    print("Creating Notion pages and databases...")
    print("This will create:")
    print("  - Inbox page (with Article, YouTube databases)")
    print("  - Index page (with Index-Inbox, Index-ToRead databases)")
    print("  - ToRead page (with ToRead database)")
    print("  - RSS_List, Tweets_List databases")
    print()

    try:
        op_notion.init()
        print()
        print("✅ Notion structure initialized successfully!")
        print(f"📖 View in Notion: https://notion.so/{page_id}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
