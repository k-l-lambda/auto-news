"""
OperatorWeb - Web page collector

Collects articles from web pages configured in Notion "Inbox - Web" database.
Supports:
- Browser mode (Playwright) for JS-rendered pages
- XPath content extraction
- Trafilatura full article extraction
- Digest splitting (extract multiple articles from index page)
- Proxy support
"""

import os
import traceback
from datetime import date, datetime
from operator import itemgetter

from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking,
    LLMAgentSummary,
)
import utils
from ops_web_base import WebCollectorBase
from db_cli import DBClient
from ops_milvus import OperatorMilvus
from ops_notion import OperatorNotion


class OperatorWeb(WebCollectorBase):
    """
    Operator for web page collection.

    Pulls web pages from Notion Inbox - Web database,
    extracts content using Trafilatura or XPath,
    supports browser mode for JS-rendered pages.
    """

    def __init__(self):
        super().__init__()
        self.source = "Web"

    def _query_web_sources(self, notion_agent, database_id):
        """
        Query Notion database for Web sources.

        Expected database schema:
        - Name: title
        - URL: url
        - Enabled: checkbox
        - XPath: text (optional)
        - Browser Mode: checkbox (optional)
        - Digest Splitting: checkbox (optional)
        - Digest Limit: number (optional)
        - Proxy: text (optional)
        """
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "descending",
                },
            ],
            "filter": {
                "and": [
                    {
                        "property": "Enabled",
                        "checkbox": {
                            "equals": True,
                        },
                    },
                ]
            }
        }

        pages = notion_agent.api.databases.query(**query_data).get("results")
        sources = []

        for page in pages:
            page_id = page["id"]
            props = page["properties"]

            # Required fields
            name = ""
            if props.get("Name", {}).get("title"):
                name = props["Name"]["title"][0]["text"]["content"]

            url = props.get("URL", {}).get("url", "")

            if not url:
                print(f"[OperatorWeb] Skipping source {name}: no URL")
                continue

            # Optional fields with defaults
            xpath = ""
            if props.get("XPath", {}).get("rich_text"):
                xpath = props["XPath"]["rich_text"][0]["text"]["content"]

            browser_mode = props.get("Browser Mode", {}).get("checkbox", False)

            digest_splitting = props.get("Digest Splitting", {}).get("checkbox", False)

            digest_limit = 30
            if props.get("Digest Limit", {}).get("number"):
                digest_limit = int(props["Digest Limit"]["number"])

            proxy = ""
            if props.get("Proxy", {}).get("rich_text"):
                proxy = props["Proxy"]["rich_text"][0]["text"]["content"]

            sources.append({
                "page_id": page_id,
                "database_id": database_id,
                "name": name,
                "url": url,
                "xpath": xpath,
                "browser_mode": browser_mode,
                "digest_splitting": digest_splitting,
                "digest_limit": digest_limit,
                "proxy": proxy,
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
            })

        return sources

    def _fetch_web_content(self, source: dict) -> list[dict]:
        """
        Fetch content from a web source.

        Args:
            source: Source configuration dict

        Returns:
            List of article dicts
        """
        name = source["name"]
        url = source["url"]

        print(f"[OperatorWeb] Fetching: {name} - {url}")

        # Configure collector from source
        self.configure_from_source(source)

        articles = []

        try:
            if self.digest_splitting:
                # Fetch multiple articles from digest/index page
                items = self.parse_digests(url, self.xpath)
                for item in items:
                    article = self._create_article(item, name)
                    articles.append(article)
            else:
                # Fetch single article
                item = self.create_news_item(url, self.xpath)
                if item["content"]:
                    article = self._create_article(item, name)
                    articles.append(article)

        except Exception as e:
            print(f"[OperatorWeb] Error fetching {url}: {e}")
            traceback.print_exc()

        finally:
            # Cleanup Playwright if used
            self.stop_playwright()

        return articles

    def _create_article(self, item: dict, list_name: str) -> dict:
        """
        Create article dict from news item.
        """
        # Generate unique ID
        hash_key = f"{list_name}_{item['title']}_{date.today().isoformat()}".encode('utf-8')
        article_id = item.get("id") or utils.hashcode_md5(hash_key)

        return {
            "id": article_id,
            "source": "Web",
            "list_name": list_name,
            "title": item["title"],
            "url": item["url"],
            "created_time": datetime.now().isoformat(),
            "summary": "",
            "content": item["content"],
            "author": item.get("author", ""),
            "tags": [],
            "published": item.get("published_date"),
        }

    def pull(self):
        """
        Pull web content from sources configured in Notion.

        @return pages dict(<id, page>)
        """
        print("#####################################################")
        print("# Pulling Web")
        print("#####################################################")

        # 1. Prepare Notion agent
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # 2. Get inbox database indexes
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Web")

        if not db_pages:
            print("[OperatorWeb] No Web inbox databases found")
            return {}

        print(f"[OperatorWeb] Found {len(db_pages)} Web inbox databases")

        # 3. Get web sources from databases
        web_sources = []
        for db_page in db_pages[:2]:  # Latest 2 databases
            database_id = db_page["database_id"]
            print(f"[OperatorWeb] Querying database: {database_id}")

            sources = self._query_web_sources(notion_agent, database_id)
            web_sources.extend(sources)

        print(f"[OperatorWeb] Found {len(web_sources)} enabled web sources")

        # 4. Fetch articles from each source
        pages = {}

        for source in web_sources:
            articles = self._fetch_web_content(source)

            for article in articles:
                page_id = article["id"]
                pages[page_id] = article
                print(f"[OperatorWeb] Collected: {article['title'][:50]}...")

        print(f"[OperatorWeb] Total articles collected: {len(pages)}")
        return pages

    def dedup(self, pages, target_sources=None):
        """
        Dedup pages using Milvus vector similarity.
        """
        print("#####################################################")
        print("# Dedup Web content")
        print("#####################################################")

        op_milvus = OperatorMilvus()
        client = DBClient()

        data = {}
        for page_id, page in pages.items():
            title = page.get("title", "")

            # Check if exists in Milvus
            if op_milvus.getIdByContent(title):
                print(f"[Dedup] Skip duplicate: {title[:50]}...")
                continue

            # Add to Milvus for future dedup
            op_milvus.addItem(title)
            data[page_id] = page

        print(f"[Dedup] {len(data)}/{len(pages)} pages after dedup")
        return data

    def summarize(self, pages):
        """
        Summarize pages using LLM.
        """
        print("#####################################################")
        print("# Summarize Web content")
        print("#####################################################")

        data = {}
        for page_id, page in pages.items():
            title = page.get("title", "")
            content = page.get("content", "")

            if not content:
                print(f"[Summarize] Skip empty content: {title[:50]}...")
                data[page_id] = page
                continue

            try:
                llm_agent = LLMAgentSummary()
                summary = llm_agent.run(content[:4000])  # Limit content length

                if summary:
                    page["summary"] = summary
                    print(f"[Summarize] Summarized: {title[:50]}...")
                else:
                    page["summary"] = content[:500]  # Fallback

            except Exception as e:
                print(f"[Summarize] Error: {e}")
                page["summary"] = content[:500]

            data[page_id] = page

        return data

    def rank(self, pages):
        """
        Rank pages using LLM.
        """
        print("#####################################################")
        print("# Rank Web content")
        print("#####################################################")

        data = {}
        for page_id, page in pages.items():
            title = page.get("title", "")
            summary = page.get("summary", "")

            try:
                llm_agent = LLMAgentCategoryAndRanking()
                result = llm_agent.run(title, summary)

                if result:
                    page["category"] = result.get("category", "")
                    page["ranking"] = result.get("ranking", 3)
                    print(f"[Rank] {title[:30]}... -> {page['category']}, score={page['ranking']}")
                else:
                    page["category"] = ""
                    page["ranking"] = 3

            except Exception as e:
                print(f"[Rank] Error: {e}")
                page["category"] = ""
                page["ranking"] = 3

            data[page_id] = page

        return data

    def push(self, pages, target_sources=None):
        """
        Push pages to Notion ToRead database.
        """
        print("#####################################################")
        print("# Push Web content to Notion")
        print("#####################################################")

        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # Get ToRead database
        db_index_id = op_notion.get_index_toread_dbid()
        db_pages = utils.get_notion_database_pages_toread(
            notion_agent, db_index_id)

        if not db_pages:
            print("[OperatorWeb] No ToRead database found")
            return

        # Use first ToRead database
        target_db_id = db_pages[0]["database_id"]
        print(f"[OperatorWeb] Pushing to database: {target_db_id}")

        # Sort by ranking (higher first)
        sorted_pages = sorted(
            pages.values(),
            key=lambda x: x.get("ranking", 3),
            reverse=True
        )

        pushed_count = 0
        for page in sorted_pages:
            try:
                notion_agent.createDatabaseItem_ToRead_Web(
                    target_db_id,
                    page
                )
                pushed_count += 1
                print(f"[Push] Pushed: {page['title'][:50]}...")

            except Exception as e:
                print(f"[Push] Error pushing {page['title'][:30]}...: {e}")

        print(f"[OperatorWeb] Pushed {pushed_count}/{len(pages)} pages")

    def save(self, pages, data_folder, target_sources=None):
        """
        Save pages to JSON file.
        """
        import json
        filepath = f"{data_folder}/web_pages.json"

        with open(filepath, 'w') as f:
            json.dump(pages, f, indent=2, default=str)

        print(f"[OperatorWeb] Saved {len(pages)} pages to {filepath}")
        return filepath

    def restore(self, data_folder, target_sources=None):
        """
        Restore pages from JSON file.
        """
        import json
        filepath = f"{data_folder}/web_pages.json"

        try:
            with open(filepath, 'r') as f:
                pages = json.load(f)
            print(f"[OperatorWeb] Restored {len(pages)} pages from {filepath}")
            return pages
        except FileNotFoundError:
            print(f"[OperatorWeb] No saved data found at {filepath}")
            return {}
