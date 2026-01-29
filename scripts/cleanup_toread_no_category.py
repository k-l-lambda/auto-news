#!/usr/bin/env python3
"""
Clean up ToRead pages without categories/topics from Notion.
Simplified version with minimal dependencies.
"""
import os
import sys

from dotenv import load_dotenv
from notion_client import Client


def cleanup_pages_without_category(dry_run=True):
    """
    Find and delete ToRead pages that have empty Category field.
    """
    notion_api_key = os.getenv("NOTION_TOKEN")
    if not notion_api_key:
        print("ERROR: NOTION_TOKEN not set")
        return

    notion = Client(auth=notion_api_key)

    # Get ToRead index database ID from environment or hardcode
    index_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")

    # First, find the Index-ToRead database
    children = notion.blocks.children.list(block_id=index_page_id)
    toread_index_db_id = None

    for child in children.get("results", []):
        if child["type"] == "child_database":
            db_id = child["id"]
            # Check if this is the Index-ToRead database
            try:
                db_info = notion.databases.retrieve(database_id=db_id)
                title = db_info.get("title", [{}])[0].get("text", {}).get("content", "")
                if "ToRead" in title and "Index" in title:
                    toread_index_db_id = db_id
                    print(f"Found Index-ToRead database: {db_id}")
                    break
            except Exception:
                continue

    if not toread_index_db_id:
        print("ERROR: Could not find Index-ToRead database")
        return

    # Get the latest ToRead database from index
    response = notion.databases.query(
        database_id=toread_index_db_id,
        sorts=[{"property": "Created time", "direction": "descending"}]
    )

    if not response["results"]:
        print("ERROR: No ToRead databases found in index")
        return

    # Get database_id property
    props = response["results"][0]["properties"]
    toread_db_id = None
    for prop_name, prop_val in props.items():
        if prop_val["type"] == "rich_text" and prop_val["rich_text"]:
            text = prop_val["rich_text"][0]["text"]["content"]
            if len(text) == 32 or "-" in text:  # UUID format
                toread_db_id = text
                break

    if not toread_db_id:
        print("ERROR: Could not get ToRead database ID from index")
        return

    print(f"ToRead database ID: {toread_db_id}")

    # Query for pages with empty Category (RSS source)
    query_data = {
        "database_id": toread_db_id,
        "filter": {
            "and": [
                {
                    "property": "Source",
                    "select": {
                        "equals": "RSS"
                    }
                },
                {
                    "property": "Category",
                    "multi_select": {
                        "is_empty": True
                    }
                }
            ]
        }
    }

    pages_to_delete = []
    has_more = True
    start_cursor = None

    while has_more:
        if start_cursor:
            query_data["start_cursor"] = start_cursor

        response = notion.databases.query(**query_data)
        pages = response.get("results", [])
        pages_to_delete.extend(pages)

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    print(f"Found {len(pages_to_delete)} RSS pages without categories")

    if dry_run:
        print("\n[DRY RUN] Would delete the following pages:")
        for page in pages_to_delete[:10]:  # Show first 10
            props = page["properties"]
            name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
            list_name = props.get("List", {}).get("select", {})
            list_name = list_name.get("name", "Unknown") if list_name else "Unknown"
            print(f"  - {name[:60]}... (List: {list_name})")
        if len(pages_to_delete) > 10:
            print(f"  ... and {len(pages_to_delete) - 10} more")
        print("\nRun with --execute to actually delete these pages")
        return

    # Delete pages (archive them)
    deleted_count = 0
    for page in pages_to_delete:
        try:
            page_id = page["id"]
            props = page["properties"]
            name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")

            print(f"Deleting: {name[:60]}...")

            # Archive the page in Notion (soft delete)
            notion.pages.update(page_id=page_id, archived=True)
            deleted_count += 1

        except Exception as e:
            print(f"ERROR deleting page: {e}")

    print(f"\nDeleted {deleted_count} pages")


if __name__ == "__main__":
    # Load environment from config
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'docker', 'workspace', 'airflow', 'config', '.env'),
        os.path.join(os.path.dirname(__file__), '..', 'build', '.env'),
        os.path.expanduser('~/.env'),
    ]

    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"Loaded env from: {env_path}")
            break

    dry_run = "--execute" not in sys.argv
    cleanup_pages_without_category(dry_run=dry_run)
