#!/usr/bin/env python3
"""
Create ToRead database and add index entry.
Run this when the ToRead index database is empty.
"""
import os
from dotenv import load_dotenv
from notion import NotionAgent
from mysql_cli import MySQLClient


def create_toread_database():
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
        return False

    # Use the ToRead database we already created
    # (If you need to create a new one, uncomment below)
    # toread_db = agent.createDatabase_ToRead("ToRead - 2026-01", toread_page_id)
    # toread_db_id = toread_db["id"]
    toread_db_id = "2f7af3ba-8af8-81b0-b91a-d5eb1c8a90c7"  # Already created
    print(f"Using ToRead database: {toread_db_id}")

    # Add entry to index database using existing "Name" property
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
    print("Done!")
    print(f"\nNOTE: Also need to update notion.py to read 'Name' property instead of 'id'")

    return True


if __name__ == "__main__":
    create_toread_database()
