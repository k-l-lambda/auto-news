#!/usr/bin/env python3
"""Test Notion connection"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from notion import NotionAgent


def test_notion_connection():
    """Test basic Notion API connection"""
    print("="*60)
    print("Testing Notion Connection")
    print("="*60)

    token = os.getenv("NOTION_TOKEN")
    page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    print(f"Token: {token[:10]}...{token[-4:]}" if token else "Token: NOT SET")
    print(f"Page ID: {page_id}" if page_id else "Page ID: NOT SET")
    print()

    if not token or not page_id:
        print("ERROR: NOTION_TOKEN or NOTION_ENTRY_PAGE_ID not set in .env")
        return False

    # Initialize Notion agent
    print("Initializing NotionAgent...")
    agent = NotionAgent(token)

    # Try to retrieve the entry page
    print(f"Retrieving page: {page_id}...")
    try:
        props, blocks = agent.extractPage(page_id, extract_blocks=False)

        if props:
            print()
            print("✓ Connection successful!")
            print(f"  Page URL: {props.get('url', 'N/A')}")
            print(f"  Created: {props.get('created_time', 'N/A')}")
            print(f"  Last edited: {props.get('last_edited_time', 'N/A')}")
            return True
        else:
            print("✗ Failed to retrieve page properties")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_create_database():
    """Test creating a simple database (optional)"""
    print()
    print("="*60)
    print("Testing Database Creation (dry-run info)")
    print("="*60)

    print("""
To fully test, Auto-news would create these databases under your page:
  - Index-Inbox: Tracks inbox databases
  - Index-ToRead: Tracks ToRead databases
  - Inbox-RSS: RSS feed items
  - ToRead: Processed items with summaries

Run 'python src/af_start.py' to initialize the full structure.
""")
    return True


if __name__ == "__main__":
    success = test_notion_connection()

    if success:
        test_create_database()
        print()
        print("="*60)
        print("Notion connection test PASSED!")
        print("="*60)
    else:
        print()
        print("="*60)
        print("Notion connection test FAILED!")
        print("Check your NOTION_TOKEN and NOTION_ENTRY_PAGE_ID")
        print("Make sure the Integration is connected to the page")
        print("="*60)
        sys.exit(1)
