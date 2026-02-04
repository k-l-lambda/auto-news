import os
import time
from datetime import date, datetime, timedelta

import pytz
import utils
from notion import NotionAgent
from ops_base import OperatorBase
from mysql_cli import MySQLClient
from ops_notion import OperatorNotion
import llm_prompts
from llm_agent import (
    LLMAgentGeneric,
    LLMAgentTranslation,
)


class OperatorDailyDigest(OperatorBase):
    """
    Operator for Daily Digest feature.
    Pulls recent ToRead items, filters by interests, and generates a daily summary.
    """

    def __init__(self):
        self.notion_agent = None
        self.op_notion = None

    def _init_notion(self):
        """Initialize Notion agent if not already done."""
        if not self.notion_agent:
            notion_api_key = os.getenv("NOTION_TOKEN")
            self.notion_agent = NotionAgent(notion_api_key)
            self.op_notion = OperatorNotion()

    def pull(self, **kwargs):
        """
        Pull ToRead items from last N hours.

        @param sources: List of sources to pull from
        @param hours_back: Number of hours to look back (default: 24)
        @return dict of pages <page_id, page>
        """
        print("#####################################################")
        print("# Pulling Pages for Daily Digest")
        print("#####################################################")
        sources = kwargs.get("sources", ["Article", "RSS", "Twitter", "Reddit", "Youtube", "Web"])
        hours_back = kwargs.get("hours_back", 24)

        # Calculate the cutoff time
        # Get timezone from environment or default to UTC
        tz_name = os.getenv("DAILY_DIGEST_TIMEZONE", "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            print(f"[WARN] Invalid timezone {tz_name}, falling back to UTC")
            tz = pytz.UTC

        now = datetime.now(tz)
        cutoff_time = now - timedelta(hours=hours_back)
        cutoff_time_iso = cutoff_time.isoformat()

        print(f"Timezone: {tz_name}, Now: {now}, Cutoff time: {cutoff_time_iso}")
        print(f"Sources: {sources}, Hours back: {hours_back}")

        self._init_notion()

        # Get ToRead database index
        db_index_id = self.op_notion.get_index_toread_dbid()
        db_pages = utils.get_notion_database_pages_toread(
            self.notion_agent, db_index_id)

        if len(db_pages) == 0:
            print("[ERROR] No valid ToRead databases found")
            return {}

        # Get the latest 2 databases
        db_pages = db_pages[:2]
        print(f"Using latest 2 ToRead databases: {db_pages}")

        page_list = {}

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            for source in sources:
                print(f"====== Pulling source: {source} ======")

                # Pull pages from cutoff time, don't require user_rating
                pages = self.notion_agent.queryDatabaseToRead(
                    database_id,
                    source,
                    last_edited_time=cutoff_time_iso,
                    extraction_interval=0.02,
                    require_user_rating=False)

                print(f"Pulled {len(pages)} pages for source: {source}")
                page_list.update(pages)

                # Wait to mitigate rate limiting
                time.sleep(2)

        print(f"Pulled total {len(page_list)} items for daily digest")
        return page_list

    def filter_by_interests(self, pages, **kwargs):
        """
        Filter pages by user rating and system rating.

        @param pages: Dict of pages to filter
        @param min_rating: Minimum rating to include (default: 3)
        @param skip_read: Skip pages where last_edited_time > created_time (default: True)
        @return dict of filtered pages
        """
        print("#####################################################")
        print("# Filter Pages by Interests")
        print("#####################################################")
        min_rating = kwargs.get("min_rating", 3)
        skip_read = kwargs.get("skip_read", True)
        print(f"Minimum rating threshold: {min_rating}, Skip read: {skip_read}")

        filtered = {}
        skipped_read = 0

        for page_id, page in pages.items():
            # Skip already read pages (edited after creation)
            if skip_read:
                created_time = page.get("created_time", "")
                last_edited_time = page.get("last_edited_time", "")
                if created_time and last_edited_time and last_edited_time > created_time:
                    skipped_read += 1
                    print(f"  [R] Already read: {page.get('name', '')[:50]}... (edited: {last_edited_time})")
                    continue

            user_rating = page.get("user_rating")

            # Get system Rating from properties
            # The structure is: page["properties"]["properties"]["Rating"]["number"]
            props = page.get("properties", {})
            if isinstance(props, dict) and "properties" in props:
                rating_prop = props.get("properties", {}).get("Rating", {})
            else:
                rating_prop = {}
            system_rating = rating_prop.get("number", 0) if isinstance(rating_prop, dict) else 0

            # Normalize system_rating if it's on 0-1 scale (Web/Arxiv uses this)
            # Convert to 1-5 scale for consistent filtering
            if system_rating and 0 < system_rating <= 1:
                system_rating = system_rating * 5  # 0.8 -> 4.0

            # Convert user_rating to int if it's a string
            user_rating_int = 0
            if user_rating:
                try:
                    user_rating_int = int(user_rating)
                except (ValueError, TypeError):
                    pass

            # Include if user_rating >= min_rating OR system Rating >= min_rating
            if user_rating_int >= min_rating or (system_rating and system_rating >= min_rating):
                filtered[page_id] = page
                print(f"  [+] Include: {page.get('name', '')[:50]}... (user_rating={user_rating}, system_rating={system_rating})")
            else:
                print(f"  [-] Exclude: {page.get('name', '')[:50]}... (user_rating={user_rating}, system_rating={system_rating})")

        print(f"Filtered from {len(pages)} to {len(filtered)} pages (skipped {skipped_read} already read)")
        return filtered

    def categorize_pages(self, pages):
        """
        Categorize pages into events, trends, and notable items.

        @param pages: Dict of pages
        @return dict with categorized pages and source stats
        """
        print("#####################################################")
        print("# Categorize Pages")
        print("#####################################################")

        # Count by source
        source_counts = {}
        for page_id, page in pages.items():
            source = page.get("source", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        print(f"Source counts: {source_counts}")

        return {
            "pages": pages,
            "source_counts": source_counts,
            "source_names": ", ".join(source_counts.keys()),
            "total_count": len(pages),
        }

    def generate_digest(self, categorized, **kwargs):
        """
        Generate structured digest using LLM.

        @param categorized: Dict with categorized pages and stats
        @param today: Date string for the digest
        @return dict with title, content, translation, sources, date
        """
        print("#####################################################")
        print("# Generate Daily Digest")
        print("#####################################################")
        today = kwargs.get("today", date.today().isoformat())
        target_lang = os.getenv("TRANSLATION_LANG")

        pages = categorized.get("pages", {})
        source_counts = categorized.get("source_counts", {})
        source_names = categorized.get("source_names", "")
        total_count = categorized.get("total_count", 0)

        if total_count == 0:
            print("[INFO] No pages to digest")
            return {
                "title": f"Daily Digest - {today}",
                "content": "No significant news items found for this period.",
                "translation": "",
                "sources": source_counts,
                "date": today,
            }

        # Prepare content for LLM
        content_parts = []
        for page_id, page in pages.items():
            title = page.get("name") or page.get("title", "Untitled")
            source = page.get("source", "Unknown")
            blocks = page.get("blocks", {})

            # Get summary from blocks
            summary = ""
            for block_id, block_data in blocks.items():
                text = block_data.get("text", "")
                if text:
                    summary += text + " "
                if len(summary) > 500:  # Limit per item
                    break

            summary = summary.strip()[:500]
            if summary:
                content_parts.append(f"[{source}] {title}\n{summary}\n")

        combined_content = "\n---\n".join(content_parts)

        # Limit total content to avoid token limits
        max_content_length = int(os.getenv("DAILY_DIGEST_MAX_CONTENT", 15000))
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "\n... [truncated]"

        print(f"Combined content length: {len(combined_content)} chars")

        # Generate digest using LLM
        if target_lang:
            prompt_template = llm_prompts.LLM_PROMPT_DAILY_DIGEST_TARGET_LANG.format(
                target_lang=target_lang)
        else:
            prompt_template = llm_prompts.LLM_PROMPT_DAILY_DIGEST

        # Escape curly braces in content to avoid LangChain PromptTemplate errors
        # (LaTeX expressions like {\\lceil n/2\\rceil} would be interpreted as variables)
        escaped_content = combined_content.replace("{", "{{").replace("}", "}}")

        # Fill in the template variables
        prompt = prompt_template.replace("{content}", escaped_content)
        prompt = prompt.replace("{source_count}", str(total_count))
        prompt = prompt.replace("{source_names}", source_names)

        llm_agent = LLMAgentGeneric()
        llm_agent.init_prompt(prompt)
        llm_agent.init_llm()

        digest_content = llm_agent.run("")
        print(f"Generated digest content ({len(digest_content)} chars)")

        # Generate title
        if target_lang:
            title_prompt = llm_prompts.LLM_PROMPT_DAILY_DIGEST_TITLE_TARGET_LANG.format(
                target_lang=target_lang)
        else:
            title_prompt = llm_prompts.LLM_PROMPT_DAILY_DIGEST_TITLE

        # Escape curly braces in digest content for title prompt
        escaped_digest = digest_content[:1000].replace("{", "{{").replace("}", "}}")
        title_prompt = title_prompt.replace("{content}", escaped_digest)

        llm_agent_title = LLMAgentGeneric()
        llm_agent_title.init_prompt(title_prompt)
        llm_agent_title.init_llm()

        title = llm_agent_title.run("")
        title = title.strip().strip('"\'')
        print(f"Generated title: {title}")

        # Generate translation if not already in target language
        translation = ""
        if target_lang and not os.getenv("DAILY_DIGEST_SKIP_TRANSLATION", "").lower() == "true":
            # If we generated in target language, translate to English for reference
            llm_agent_trans = LLMAgentTranslation()
            llm_agent_trans.init_prompt(trans_lang="English")
            llm_agent_trans.init_llm()
            translation = llm_agent_trans.run(digest_content)
            print(f"Generated English translation ({len(translation)} chars)")

        # Collect source page info for linking
        source_pages = []
        for page_id, page in pages.items():
            source_pages.append({
                "id": page_id,
                "title": page.get("name") or page.get("title", "Untitled"),
                "source": page.get("source", "Unknown"),
                "notion_url": page.get("notion_url", ""),
            })

        return {
            "title": f"{today} - {title}",
            "content": digest_content,
            "translation": translation,
            "sources": source_counts,
            "source_pages": source_pages,  # For linking to original articles
            "date": today,
        }

    def push(self, digest, targets, **kwargs):
        """
        Push digest to targets (e.g., Notion ToRead).

        @param digest: Dict with digest content
        @param targets: List of target names
        """
        print("#####################################################")
        print("# Push Daily Digest")
        print("#####################################################")
        print(f"Targets: {targets}")
        print(f"Digest title: {digest.get('title')}")

        for target in targets:
            print(f"Pushing to target: {target}...")

            if target == "notion":
                self._push_to_notion(digest)
            else:
                print(f"[WARN] Unknown target: {target}, skipping")

    def _push_to_notion(self, digest):
        """Push digest to Notion Daily Digest database."""
        self._init_notion()

        # Use dedicated Daily Digest database if configured
        database_id = os.getenv("NOTION_DATABASE_ID_DAILY_DIGEST")

        if not database_id:
            # Try to get daily_digest_db_id from indexes
            db_client = MySQLClient()
            indexes = db_client.index_pages_table_load()
            daily_digest_index = indexes.get("notion", {}).get("daily_digest_db_id", {})
            if daily_digest_index:
                database_id = daily_digest_index.get("index_id")
                print(f"Using daily_digest_db_id from indexes: {database_id}")

        if not database_id:
            # Fallback to ToRead database
            print("[WARN] No Daily Digest database found, falling back to ToRead")
            db_index_id = self.op_notion.get_index_toread_dbid()
            database_id = utils.get_notion_database_id_toread(
                self.notion_agent, db_index_id)

        if not database_id:
            print("[ERROR] No database found, cannot push digest")
            return

        print(f"Pushing to Daily Digest database: {database_id}")

        try:
            self.notion_agent.createDatabaseItem_ToRead_DailyDigest(
                database_id,
                digest)
            print("[SUCCESS] Daily digest pushed to Notion")

        except Exception as e:
            print(f"[ERROR] Failed to push digest to Notion: {e}")
            raise
