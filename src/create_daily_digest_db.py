#!/usr/bin/env python3
"""
Script to create Daily Digest database in Notion.
Run once to initialize the database, then add the database ID to .env:
    NOTION_DATABASE_ID_DAILY_DIGEST=<database_id>
"""
import os
from dotenv import load_dotenv

from notion import NotionAgent
from mysql_cli import MySQLClient


def create_daily_digest_database():
    """Create Daily Digest database in Notion under ToRead page."""
    load_dotenv()

    notion_api_key = os.getenv("NOTION_TOKEN")
    agent = NotionAgent(notion_api_key)
    db_cli = MySQLClient()

    # Load existing indexes
    indexes = db_cli.index_pages_table_load()
    print(f"Loaded indexes: {indexes}")

    notion_indexes = indexes.get("notion", {})

    # Check if already exists
    existing_db_id = notion_indexes.get("daily_digest_db_id")
    if existing_db_id:
        print(f"[INFO] Daily Digest database already exists: {existing_db_id['index_id']}")
        print(f"\nAdd to .env:\nNOTION_DATABASE_ID_DAILY_DIGEST={existing_db_id['index_id']}")
        return existing_db_id['index_id']

    # Get parent page (use ToRead page as parent)
    toread_page_id = notion_indexes.get("toread_page_id", {}).get("index_id")
    if not toread_page_id:
        print("[ERROR] ToRead page not found. Please run the main setup first.")
        return None

    print(f"Creating Daily Digest database under ToRead page: {toread_page_id}")

    # Create the database
    new_db = agent.createDatabase_DailyDigest(
        "Daily Digest",
        toread_page_id
    )

    database_id = new_db["id"]
    print(f"[SUCCESS] Created Daily Digest database: {database_id}")

    # Save to MySQL index
    db_cli.index_pages_table_insert(
        "notion", "daily_digest_db_id", database_id)
    print("[SUCCESS] Saved database ID to MySQL index")

    print(f"\n{'='*60}")
    print("Add the following to your .env file:")
    print(f"NOTION_DATABASE_ID_DAILY_DIGEST={database_id}")
    print(f"{'='*60}")

    return database_id


if __name__ == "__main__":
    create_daily_digest_database()
