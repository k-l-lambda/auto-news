#!/usr/bin/env python3
"""Check Index-ToRead database properties"""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))

# Index ToRead DB ID
db_id = "e5f65477-99d2-49eb-b145-79db1879e5da"

print("Retrieving database info...")
db_info = notion.databases.retrieve(database_id=db_id)

print(f"\nDatabase title: {db_info.get('title', [{}])[0].get('plain_text', 'N/A')}")
print(f"\nProperties:")
for prop_name, prop_info in db_info.get("properties", {}).items():
    print(f"  - {prop_name}: {prop_info.get('type')}")
