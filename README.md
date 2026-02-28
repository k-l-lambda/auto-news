# Auto-News: Automated News Aggregator with LLM

[![GitHub Build](https://github.com/finaldie/auto-news/actions/workflows/python.yml/badge.svg)](https://github.com/finaldie/auto-news/actions)

> Fork of [finaldie/auto-news](https://github.com/finaldie/auto-news) with custom enhancements for personal use.

LLM-powered news aggregation pipeline: RSS/Reddit/Web → Airflow → Notion, with intelligent scoring, filtering, and structured summaries.

## Architecture

```
RSS / Reddit / Web sources
        ↓
   Airflow DAGs (news_pulling, sync_dist)
        ↓
   Notion ToRead DB (with LLM scoring & categorization)
        ↓
   [OpenClaw Agent — scan, score, pick]
        ↓
   Agent Picks DB → Deep Dive / Daily Digest / Weekly Recap
```

### Core Components
- **Airflow Pipeline**: Pulls content from RSS, Reddit, Web sources on schedule
- **Milvus Vector DB**: Embedding-based similarity scoring for content filtering
- **MySQL**: Source management, metadata, dedup state
- **Notion**: Reading interface — ToRead DB (raw articles) + Agent Picks DB (curated)
- **LLM Backend**: OpenAI GPT / Google Gemini / Ollama for summarization and scoring

## Features

- Aggregate feed sources (RSS, Reddit, Web) with LLM-generated insights
- YouTube video transcription and summarization
- Content ranking & classification with vector embeddings
- Configurable top-k filtering based on personal interests (removes 80%+ noise)
- Rich text summaries in Notion (Markdown → native Notion blocks: headings, bold, lists)
- Multi-language summary output (direct generation, no translation step)
- Weekly Top-k Recap
- Dynamic ToRead DB rotation (auto-create on Notion schema overflow)

## Fork Enhancements

Changes made in this fork on top of upstream:

### Notion API Resilience
- Exponential backoff retry on 429 rate limiting (all API paths)
- `sync_dist` resilient to rate limits during batch sync
- `daily_digest` increased throttle intervals
- Auto-fix Notion schema overflow during push

### Data Quality
- **Source URL in ToRead**: Article URLs now written to the "To" property (rich_text + href), accessible without parsing page blocks
- Daily date format (`YYYY-MM-DD`) for ToRead database names
- Consolidated categories to a fixed set
- Lowered RSS LLM score threshold from 0.85 → 0.75 (configurable)

### Bug Fixes
- Daily Digest crash on LaTeX curly braces in content
- Daily Digest title uses actual date in configured timezone
- Correct MySQL client for Daily Digest database selection
- Notion block limit handling for Daily Digest
- RSS processing timeout and LLM API resilience
- Reuse EmbeddingAgent in scoring to avoid repeated model loading

## Deployment

### System Requirements

| Component | Minimum      | Recommended  |
| --------- | ------------ | ------------ |
| OS        | Linux, MacOS | Linux, MacOS |
| CPU       | 2 cores      | 8 cores      |
| Memory    | 6GB          | 16GB         |
| Disk      | 20GB         | 100GB        |

### Docker Compose (recommended)

```bash
cd docker
docker compose up -d
```

Key services: `airflow-worker`, `airflow-scheduler`, `airflow-webserver`, `mysql-db`, `milvus`, `redis`, `postgres`

### Other Options
- [Docker-compose guide](https://github.com/finaldie/auto-news/wiki/Docker-Installation)
- [Kubernetes / Helm](https://github.com/finaldie/auto-news/wiki/Installation-using-Helm)
- [ArgoCD](https://github.com/finaldie/auto-news/wiki/Installation-using-ArgoCD)

## Documentation

See the upstream wiki: https://github.com/finaldie/auto-news/wiki

## Credits

Based on [auto-news](https://github.com/finaldie/auto-news) by [finaldie](https://github.com/finaldie).
