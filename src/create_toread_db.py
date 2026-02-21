#!/usr/bin/env python3
"""
Create ToRead database and add index entry.
Run this script when schema overflow is detected or manually to create a new ToRead database.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from notion import NotionAgent
from mysql_cli import MySQLClient


def create_toread_database(date_name=None):
    """
    Create a new ToRead database for the specified date.

    Args:
        date_name: Optional date string in YYYY-MM-DD format.
                   If not provided, uses current date.

    Returns:
        The new database ID string on success, or None on failure.
    """
    load_dotenv()

    notion_api_key = os.getenv("NOTION_TOKEN")
    agent = NotionAgent(notion_api_key)

    db_cli = MySQLClient()
    indexes = db_cli.index_pages_table_load()
    print(f"Loaded indexes: {indexes}")

    notion_indexes = indexes.get("notion", {})

    # Get the ToRead page ID and index database ID
    toread_page_id = notion_indexes.get("toread_page_id", {}).get("index_id")
    index_toread_db_id = notion_indexes.get("index_toread_db_id", {}).get("index_id")

    print(f"ToRead page ID: {toread_page_id}")
    print(f"Index ToRead DB ID: {index_toread_db_id}")

    if not toread_page_id or not index_toread_db_id:
        print("[ERROR] Missing toread_page_id or index_toread_db_id in indexes")
        return None

    # Determine the date name for the database
    if not date_name:
        date_name = datetime.now().strftime("%Y-%m-%d")

    db_name = f"ToRead - {date_name}"
    print(f"Creating ToRead database: {db_name}")

    # Create the new ToRead database
    toread_db = agent.createDatabase_ToRead(db_name, toread_page_id)
    toread_db_id = toread_db["id"]
    print(f"Created ToRead database: {toread_db_id}")

    # Add entry to index database
    print("Adding entry to index database...")
    from notion_client import Client
    notion = Client(auth=notion_api_key)

    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": toread_db_id
                    }
                }
            ]
        }
    }

    notion.pages.create(
        parent={"database_id": index_toread_db_id},
        properties=properties
    )
    print(f"Done! Created and indexed ToRead database for {date_name}")

    return toread_db_id


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create ToRead database")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    create_toread_database(args.date)
