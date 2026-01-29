#!/usr/bin/env python3
"""
Import seed articles to Milvus for recommendation scoring.

This script imports user-curated article links to solve the Cold Start problem.
Articles are added to Milvus with high user_rating (5) so new similar articles
will receive high relevance scores.

Usage:
    python scripts/import_seeds.py --file /path/to/seeds.md
    python scripts/import_seeds.py --file /tmp/arxiv_seeds.md --user-rating 5
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv


def parse_arxiv_md(file_path: str) -> list:
    """
    Parse arxiv.md file and extract paper IDs and titles.

    Returns list of dicts: [{"arxiv_id": "2305.18290", "title": "DPO..."}, ...]
    """
    papers = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: [*arxiv_id*](https://arxiv.org/abs/arxiv_id) | **title** |
    pattern = r'\[\*([0-9.]+)\*\]\(https://arxiv\.org/abs/[^)]+\)\s*\|\s*\*\*([^*]+)\*\*'

    matches = re.findall(pattern, content)

    for arxiv_id, title in matches:
        papers.append({
            "arxiv_id": arxiv_id.strip(),
            "title": title.strip()
        })

    print(f"Parsed {len(papers)} papers from {file_path}")
    return papers


def parse_reading_md(file_path: str) -> list:
    """
    Parse reading.md file and extract book titles with their notes.

    Format:
    ## 《Book Title》 or ## Book Title
    ### [date](...)
    notes content...

    Returns list of dicts: [{"book_id": "hash", "title": "...", "content": "..."}, ...]
    """
    import hashlib

    books = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by ## headers (book titles)
    sections = re.split(r'\n## ', content)

    for section in sections[1:]:  # Skip first empty section
        lines = section.strip().split('\n')
        if not lines:
            continue

        # First line is the title
        title_line = lines[0].strip()

        # Skip MENU section
        if title_line == 'MENU':
            continue

        # Extract title (remove 《》 if present)
        title = re.sub(r'[《》]', '', title_line).strip()

        if not title:
            continue

        # Collect content (all lines after title, excluding date headers)
        content_lines = []
        for line in lines[1:]:
            # Skip date headers like ### [2024/0113](...)
            if re.match(r'^###\s*\[[\d/]+\]', line):
                continue
            # Skip empty lines at start
            if not content_lines and not line.strip():
                continue
            content_lines.append(line)

        # Join content, limit to reasonable size
        notes = '\n'.join(content_lines).strip()

        # Only include if there's meaningful content
        if len(notes) < 10:
            notes = title  # Use title as content if notes too short

        # Truncate very long content
        if len(notes) > 2000:
            notes = notes[:2000] + "..."

        book_id = hashlib.md5(title.encode('utf-8')).hexdigest()[:12]

        books.append({
            "book_id": f"reading_{book_id}",
            "title": title,
            "content": f"{title}\n\n{notes}"
        })

    print(f"Parsed {len(books)} books/entries from {file_path}")
    return books


def fetch_arxiv_abstract(arxiv_id: str, proxy: str = None) -> str:
    """
    Fetch abstract from arxiv API.

    API: https://export.arxiv.org/api/query?id_list=arxiv_id
    """
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"

    try:
        if proxy:
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy,
                'https': proxy
            })
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Auto-News/1.0 (https://github.com/example/auto-news)'
        })

        with urllib.request.urlopen(req, timeout=30) as response:
            xml_content = response.read().decode('utf-8')

        # Parse XML
        root = ET.fromstring(xml_content)

        # Namespace handling
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        # Find summary (abstract)
        entry = root.find('atom:entry', ns)
        if entry is not None:
            summary = entry.find('atom:summary', ns)
            if summary is not None and summary.text:
                # Clean up whitespace
                abstract = ' '.join(summary.text.split())
                return abstract

        return ""

    except Exception as e:
        print(f"[WARN] Failed to fetch abstract for {arxiv_id}: {e}")
        return ""


def import_reading_to_milvus(books: list, user_rating: int = 5, batch_size: int = 10):
    """
    Import reading entries (books, notes) to Milvus collection.
    No external API calls needed - content is already in the file.
    """
    from db_cli import DBClient
    from milvus_cli import MilvusClient
    from embedding_agent import EmbeddingAgent

    # Initialize clients
    db_client = DBClient()
    emb_agent = EmbeddingAgent()
    milvus_client = MilvusClient(emb_agent=emb_agent)

    # Use today's date for collection name
    start_date = date.today().isoformat()
    collection_name = emb_agent.getname(start_date)

    print(f"Collection name: {collection_name}")
    print(f"Embedding model: {emb_agent.model_name}, dim: {emb_agent.dim()}")

    # Create collection if not exists
    if not milvus_client.exist(collection_name):
        milvus_client.createCollection(
            collection_name,
            desc=f"Seed collection for {start_date}, dim: {emb_agent.dim()}",
            dim=emb_agent.dim()
        )
        print(f"Created new collection: {collection_name}")
    else:
        milvus_client.loadCollection(collection_name)
        print(f"Using existing collection: {collection_name}")

    # Import books
    imported = 0
    skipped = 0
    errors = 0
    key_ttl = 86400 * 90  # 90 days for seed data

    for i, book in enumerate(books):
        page_id = book["book_id"]
        title = book["title"]
        content = book["content"]

        print(f"\n[{i+1}/{len(books)}] Processing: {title[:50]}...")

        # Check if already imported
        existing = db_client.get_page_item_id(page_id)
        if existing:
            print(f"  Already imported, skipping")
            skipped += 1
            continue

        try:
            # Create embedding
            embedding = emb_agent.get_or_create(
                content,
                source="reading_seed",
                page_id=page_id,
                db_client=db_client,
                key_ttl=key_ttl
            )

            # Add to Milvus
            milvus_client.add(
                collection_name,
                page_id,
                content,
                embed=embedding
            )

            # Store metadata in Redis
            metadata = {
                "page_id": page_id,
                "user_rating": user_rating,
                "title": title,
                "source": "reading_seed"
            }
            db_client.set_page_item_id(page_id, json.dumps(metadata), expired_time=key_ttl)

            imported += 1
            print(f"  Imported successfully")

            # Batch checkpoint
            if (i + 1) % batch_size == 0:
                print(f"\n[Batch checkpoint] Imported: {imported}, Skipped: {skipped}, Errors: {errors}")

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")
            errors += 1

    # Flush collection
    milvus_client.flush(collection_name)

    print(f"\n{'='*60}")
    print(f"Import Summary:")
    print(f"  Total entries: {len(books)}")
    print(f"  Imported: {imported}")
    print(f"  Skipped (duplicate): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Collection: {collection_name}")

    # Show collection stats
    stats = milvus_client.get_stats(collection_name)
    print(f"  Collection entities: {stats['num_entities']}")


def import_to_milvus(papers: list, user_rating: int = 5, batch_size: int = 10):
    """
    Import papers to Milvus collection.
    """
    from db_cli import DBClient
    from milvus_cli import MilvusClient
    from embedding_agent import EmbeddingAgent
    import utils

    # Initialize clients
    db_client = DBClient()
    emb_agent = EmbeddingAgent()
    milvus_client = MilvusClient(emb_agent=emb_agent)

    # Use today's date for collection name
    start_date = date.today().isoformat()
    collection_name = emb_agent.getname(start_date)

    print(f"Collection name: {collection_name}")
    print(f"Embedding model: {emb_agent.model_name}, dim: {emb_agent.dim()}")

    # Create collection if not exists
    if not milvus_client.exist(collection_name):
        milvus_client.createCollection(
            collection_name,
            desc=f"Seed collection for {start_date}, dim: {emb_agent.dim()}",
            dim=emb_agent.dim()
        )
        print(f"Created new collection: {collection_name}")
    else:
        milvus_client.loadCollection(collection_name)
        print(f"Using existing collection: {collection_name}")

    # Import papers
    imported = 0
    skipped = 0
    errors = 0
    key_ttl = 86400 * 90  # 90 days for seed data

    proxy = os.getenv("HTTP_PROXY", "")

    for i, paper in enumerate(papers):
        arxiv_id = paper["arxiv_id"]
        title = paper["title"]
        page_id = f"arxiv_{arxiv_id}"

        print(f"\n[{i+1}/{len(papers)}] Processing: {arxiv_id} - {title[:50]}...")

        # Check if already imported
        existing = db_client.get_page_item_id(page_id)
        if existing:
            print(f"  Already imported, skipping")
            skipped += 1
            continue

        try:
            # Fetch abstract
            abstract = fetch_arxiv_abstract(arxiv_id, proxy=proxy)

            if not abstract:
                print(f"  No abstract found, using title only")
                content = title
            else:
                content = f"{title}\n\n{abstract}"
                print(f"  Abstract length: {len(abstract)} chars")

            # Create embedding
            embedding = emb_agent.get_or_create(
                content,
                source="arxiv_seed",
                page_id=page_id,
                db_client=db_client,
                key_ttl=key_ttl
            )

            # Add to Milvus
            milvus_client.add(
                collection_name,
                page_id,
                content,
                embed=embedding
            )

            # Store metadata in Redis
            metadata = {
                "page_id": page_id,
                "user_rating": user_rating,
                "arxiv_id": arxiv_id,
                "title": title,
                "source": "arxiv_seed"
            }
            db_client.set_page_item_id(page_id, json.dumps(metadata), expired_time=key_ttl)

            imported += 1
            print(f"  Imported successfully")

            # Rate limiting
            if (i + 1) % batch_size == 0:
                print(f"\n[Batch checkpoint] Imported: {imported}, Skipped: {skipped}, Errors: {errors}")
                time.sleep(1)  # Be nice to arxiv API

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")
            errors += 1

    # Flush collection
    milvus_client.flush(collection_name)

    print(f"\n{'='*60}")
    print(f"Import Summary:")
    print(f"  Total papers: {len(papers)}")
    print(f"  Imported: {imported}")
    print(f"  Skipped (duplicate): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Collection: {collection_name}")

    # Show collection stats
    stats = milvus_client.get_stats(collection_name)
    print(f"  Collection entities: {stats['num_entities']}")


def main():
    parser = argparse.ArgumentParser(description="Import seed articles to Milvus")
    parser.add_argument("--file", required=True, help="Path to seed file (markdown)")
    parser.add_argument("--type", choices=["arxiv", "reading", "auto"], default="auto",
                        help="Type of seed file: arxiv, reading, or auto-detect (default: auto)")
    parser.add_argument("--user-rating", type=int, default=5,
                        help="User rating for imported articles (1-5, default: 5)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Batch size for rate limiting (default: 10)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of entries to import (0 = all)")

    args = parser.parse_args()

    # Load environment
    load_dotenv()

    # Auto-detect file type
    file_type = args.type
    if file_type == "auto":
        if "arxiv" in args.file.lower():
            file_type = "arxiv"
        elif "reading" in args.file.lower():
            file_type = "reading"
        else:
            # Try to detect by content
            with open(args.file, 'r', encoding='utf-8') as f:
                sample = f.read(1000)
            if "arxiv.org" in sample:
                file_type = "arxiv"
            else:
                file_type = "reading"
        print(f"Auto-detected file type: {file_type}")

    if file_type == "arxiv":
        # Parse arxiv seed file
        papers = parse_arxiv_md(args.file)

        if args.limit > 0:
            papers = papers[:args.limit]
            print(f"Limited to first {args.limit} papers")

        if not papers:
            print("No papers found to import")
            return

        # Import to Milvus (with arxiv API fetch)
        import_to_milvus(papers, user_rating=args.user_rating, batch_size=args.batch_size)

    elif file_type == "reading":
        # Parse reading seed file
        books = parse_reading_md(args.file)

        if args.limit > 0:
            books = books[:args.limit]
            print(f"Limited to first {args.limit} entries")

        if not books:
            print("No entries found to import")
            return

        # Import to Milvus (no external API needed)
        import_reading_to_milvus(books, user_rating=args.user_rating, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
