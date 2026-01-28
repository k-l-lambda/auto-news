#!/usr/bin/env python3
"""
Reinitialize Notion indexes in MySQL to use the correct databases.

This script:
1. Creates proper Index - Inbox database with correct properties
2. Creates entries in Index - Inbox pointing to RSS_List
3. Updates MySQL indexes to point to the new databases
"""

import os
import sys
import httpx
import mysql.connector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()


def get_notion_headers():
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_TOKEN')}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }


def create_index_database(parent_page_id: str, title: str) -> str:
    """Create an Index database with proper properties."""
    headers = get_notion_headers()

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": {
            "id": {"title": {}},  # This is the target database_id (title type expected by code)
            "Source": {
                "select": {
                    "options": [
                        {"name": "RSS", "color": "green"},
                        {"name": "Twitter", "color": "blue"},
                        {"name": "Article", "color": "yellow"},
                        {"name": "Youtube", "color": "red"},
                        {"name": "Reddit", "color": "orange"},
                        {"name": "Web", "color": "purple"},
                        {"name": "ToRead", "color": "gray"},
                    ]
                }
            },
            "Created time": {"created_time": {}},
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

    return response.json()["id"]


def create_index_entry(index_db_id: str, target_db_id: str, source: str, description: str):
    """Create an entry in the index database."""
    headers = get_notion_headers()

    # The 'id' property (title type) contains the target database_id
    payload = {
        "parent": {"database_id": index_db_id},
        "properties": {
            "id": {"title": [{"text": {"content": target_db_id}}]},
            "Source": {"select": {"name": source}},
        }
    }

    with httpx.Client() as client:
        response = client.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload,
            timeout=30.0
        )

    if response.status_code != 200:
        raise Exception(f"Failed to create entry: {response.text}")

    return response.json()["id"]


def update_mysql_index(name: str, index_id: str):
    """Update MySQL index_pages table."""
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
    cursor = conn.cursor()

    # Check if entry exists
    cursor.execute(
        "SELECT id FROM index_pages WHERE category='notion' AND name=%s",
        (name,)
    )
    result = cursor.fetchone()

    if result:
        cursor.execute(
            "UPDATE index_pages SET index_id=%s, updated_at=NOW() WHERE category='notion' AND name=%s",
            (index_id, name)
        )
        print(f"  Updated {name} -> {index_id[:8]}...")
    else:
        cursor.execute(
            "INSERT INTO index_pages (category, name, index_id, created_at, updated_at) VALUES ('notion', %s, %s, NOW(), NOW())",
            (name, index_id)
        )
        print(f"  Inserted {name} -> {index_id[:8]}...")

    conn.commit()
    cursor.close()
    conn.close()


def main():
    print("=" * 60)
    print("Reinitializing Notion Indexes")
    print("=" * 60)

    entry_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")
    rss_list_db_id = os.getenv("RSS_LIST_DB_ID")

    if not entry_page_id or not rss_list_db_id:
        print("[ERR] NOTION_ENTRY_PAGE_ID and RSS_LIST_DB_ID must be set")
        sys.exit(1)

    # Get index_page_id from MySQL
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
    cursor = conn.cursor()
    cursor.execute("SELECT index_id FROM index_pages WHERE category='notion' AND name='index_page_id'")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        print("[ERR] index_page_id not found in MySQL")
        sys.exit(1)

    index_page_id = result[0]
    print(f"Index Page ID: {index_page_id}")
    print(f"RSS List DB ID: {rss_list_db_id}")

    # Step 1: Create new Index - Inbox database
    print("\n[1] Creating Index - Inbox database...")
    index_inbox_db_id = create_index_database(index_page_id, "Index - Inbox (New)")
    print(f"    Created: {index_inbox_db_id[:8]}...")

    # Step 2: Create entry for RSS in index
    print("\n[2] Creating RSS entry in index...")
    create_index_entry(
        index_inbox_db_id,
        rss_list_db_id,
        "RSS",
        "RSS Feed Sources"
    )
    print("    Created RSS entry")

    # Step 3: Update MySQL indexes
    print("\n[3] Updating MySQL indexes...")
    update_mysql_index("index_inbox_db_id", index_inbox_db_id)
    update_mysql_index("index_rss_list_db_id", rss_list_db_id)

    print("\n" + "=" * 60)
    print("[OK] Initialization complete!")
    print("=" * 60)
    print("\nNew database IDs:")
    print(f"  index_inbox_db_id: {index_inbox_db_id}")
    print(f"  index_rss_list_db_id: {rss_list_db_id}")


if __name__ == "__main__":
    main()
