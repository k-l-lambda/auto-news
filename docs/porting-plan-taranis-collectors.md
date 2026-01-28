# Porting Plan: Taranis Collector Patterns to Auto-News

## Overview

Port Taranis AI's mature collector patterns to Auto-News while preserving Auto-News's LLM pipeline architecture.

**Base Project:** Auto-News (`.`)
**Source Project:** Taranis AI (`../others/taranis-ai`)

---

## Features to Port

| Feature | Taranis Source | Priority | Complexity |
|---------|---------------|----------|------------|
| Playwright Browser Mode | `playwright_manager.py` | **P0** | Medium |
| XPath Extraction | `base_web_collector.py:124-134` | **P0** | Low |
| Trafilatura Full Article | `base_web_collector.py:165-177` | **P0** | Low |
| Digest Splitting | `base_web_collector.py:184-197` | **P0** | Medium |
| If-Modified-Since | `base_web_collector.py:48-56` | P1 | Low |
| Proxy Support | `base_web_collector.py:77` | P1 | Low |
| Word List Filtering | `base_collector.py:filter_by_word_list` | P2 | Low |

**User Priority: New Web Collector (Phase 3-4 first)**

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| **Phase 1: Core Infrastructure** | | |
| 1.1 WebCollectorBase class | ✅ Done | `src/ops_web_base.py` |
| 1.2 PlaywrightManager class | ✅ Done | `src/playwright_manager.py` |
| 1.3 Add dependencies | ✅ Done | `pyproject.toml` (playwright, trafilatura, lxml) |
| **Phase 3: Web Collector** | | |
| 3.1 OperatorWeb class | ✅ Done | `src/ops_web.py` |
| 3.2 Notion Web database | ✅ Done | Query method in ops_web.py |
| **Phase 4: Pipeline Integration** | | |
| 4.1 Update af_pull.py | ✅ Done | Added Web source |
| 4.2 Update af_save.py | ✅ Done | Added process_web() |
| 4.3 Notion ToRead method | ✅ Done | `createDatabaseItem_ToRead_Web` in notion.py |
| **Phase 2: RSS Enhancement** | | |
| 2.1 Upgrade OperatorRSS | ✅ Done | Browser mode, XPath, Full article |
| **Phase 5: Advanced** | | |
| 5.1 MISP Collector | ⏳ Optional | |
| 5.2 Word List Filtering | ⏳ Optional | |

---

## Implementation Plan

> **Execution Order:** Phase 1 → Phase 3 → Phase 4 → Phase 2 → Phase 5
> (Core infra first, then Web Collector, then RSS enhancement)

### Phase 1: Core Infrastructure

**1.1 Create WebCollectorBase class**
- File: `src/ops_web_base.py` (new)
- Extend `OperatorBase` with web collection utilities
- Port from Taranis: `base_web_collector.py`

```python
class WebCollectorBase(OperatorBase):
    def __init__(self):
        self.proxies = None
        self.headers = {"User-Agent": "Auto-News/1.0"}
        self.browser_mode = False
        self.xpath = ""
        self.playwright_manager = None

    def send_get_request(url, modified_since=None) -> Response
    def fetch_article_content(url, xpath="") -> tuple[str, datetime]
    def xpath_extraction(html, xpath) -> str
    def extract_web_content(url, xpath="") -> dict
```

**1.2 Create PlaywrightManager class**
- File: `src/playwright_manager.py` (new)
- Port from: `../others/taranis-ai/src/worker/worker/collectors/playwright_manager.py`

```python
class PlaywrightManager:
    def __init__(proxies=None, headers=None)
    def setup_context(headers=None) -> BrowserContext
    def fetch_content_with_js(url, xpath="") -> str
    def stop_playwright_if_needed()
```

**1.3 Add dependencies**
- File: `docker/requirements.txt`
- Add: `playwright`, `trafilatura`, `lxml`

---

### Phase 2: Enhance Existing RSS Collector

**2.1 Upgrade OperatorRSS**
- File: `src/ops_rss.py`
- Inherit from `WebCollectorBase` instead of `OperatorBase`
- Add features:

| Feature | Implementation |
|---------|---------------|
| If-Modified-Since | Track `last_modified` per feed in Redis |
| Full Article Fetch | Use Trafilatura when RSS has truncated content |
| Browser Mode | Playwright for JS-rendered feeds |
| XPath Extraction | Custom content selection |

**2.2 Configuration Schema (Notion Inbox)**

Add new columns to RSS Inbox database:
```
| Column | Type | Default | Description |
|--------|------|---------|-------------|
| Browser Mode | Checkbox | false | Enable JS rendering |
| XPath | Text | "" | Content selection path |
| Proxy | Text | "" | HTTP proxy URL |
| Fetch Full Article | Checkbox | false | Trafilatura extraction |
```

---

### Phase 3: New Simple Web Collector

**3.1 Create OperatorWeb**
- File: `src/ops_web.py` (new)
- Port from: `../others/taranis-ai/src/worker/worker/collectors/simple_web_collector.py`

```python
class OperatorWeb(WebCollectorBase):
    def pull(self):
        """Scrape web pages from Notion Inbox - Web database"""
        # 1. Query Notion for web sources
        # 2. For each source:
        #    - Fetch with optional browser mode
        #    - Extract content via XPath or Trafilatura
        #    - Create news item
        # 3. Support digest splitting (extract links from index page)
```

**3.2 Notion Database Setup**
- Create "Inbox - Web" database in Notion
- Schema:
```
| Column | Type | Required |
|--------|------|----------|
| Name | Title | Yes |
| URL | URL | Yes |
| XPath | Text | No |
| Browser Mode | Checkbox | No |
| Digest Splitting | Checkbox | No |
| Digest Limit | Number | No (default: 30) |
| Proxy | Text | No |
| Last Modified | Date | Auto |
```

---

### Phase 4: Pipeline Integration

**4.1 Update af_pull.py**
```python
CONTENT_SOURCES = "Twitter,Reddit,Article,Youtube,RSS,Web"  # Add Web

# In run_pull():
if "Web" in sources:
    op_web = OperatorWeb()
    op_web.pull()
```

**4.2 Update af_save.py**
```python
def process_web(op):
    """Process web collector output"""
    op.dedup()
    op.summarize()  # LLM summarization
    op.rank()       # LLM ranking
    op.push()       # Push to Notion ToRead
```

**4.3 Update Airflow DAG**
- File: `dags/news_pulling.py`
- Add Web to pipeline

---

### Phase 5: Advanced Features (Optional)

**5.1 MISP Collector (Security Intelligence)**
- File: `src/ops_misp.py` (new)
- Port from: Taranis `misp_collector.py`
- Requires: PyMISP library
- For: Threat intelligence feeds

**5.2 Word List Filtering**
- File: `src/word_filter.py` (new)
- Include/exclude content by keyword lists
- Integration point: `OperatorBase.filter()`

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/ops_web_base.py` | Create | Base class for web collectors |
| `src/playwright_manager.py` | Create | Playwright browser automation |
| `src/ops_web.py` | Create | Simple web collector |
| `src/ops_rss.py` | Modify | Add browser mode, XPath, Trafilatura |
| `src/af_pull.py` | Modify | Add Web to CONTENT_SOURCES |
| `src/af_save.py` | Modify | Add process_web() |
| `dags/news_pulling.py` | Modify | Include Web in pipeline |
| `docker/requirements.txt` | Modify | Add playwright, trafilatura, lxml |
| `.env.template` | Modify | Add WEB_PROXY, BROWSER_MODE env vars |

---

## Key Code Mappings

| Taranis File | Auto-News Target | Lines to Port |
|--------------|-----------------|---------------|
| `base_web_collector.py` | `ops_web_base.py` | 48-56, 77, 124-134, 165-177, 184-197 |
| `playwright_manager.py` | `playwright_manager.py` | Full file (67 lines) |
| `simple_web_collector.py` | `ops_web.py` | Core logic |
| `rss_collector.py` | `ops_rss.py` | Full article fetch, digest splitting |

---

## Testing Plan

1. **Unit Tests**
   - `tests/test_web_base.py` - XPath extraction, If-Modified-Since
   - `tests/test_playwright.py` - Browser mode with mock

2. **Integration Tests**
   - RSS with full article fetch
   - Web collector with digest splitting
   - Browser mode on JS-heavy site

3. **End-to-End Test**
   ```bash
   # Run pipeline with Web collector
   cd ../auto-news
   python src/af_pull.py --sources Web
   python src/af_save.py --sources Web
   ```

---

## Dependencies

```
# Add to docker/requirements.txt
playwright>=1.40.0
trafilatura>=1.6.0
lxml>=4.9.0
```

```bash
# Post-install
playwright install chromium
```

---

## Estimated Scope

- **Phase 1-2:** Core infrastructure + RSS enhancement
- **Phase 3-4:** New web collector + pipeline integration
- **Phase 5:** Optional advanced features

---

## Reference Files

**Auto-News (base):**
- `src/ops_base.py` - OperatorBase class
- `src/ops_rss.py` - Current RSS collector
- `src/af_pull.py` - Pull orchestration
- `src/af_save.py` - Processing pipeline
- `src/notion.py` - Notion integration

**Taranis (source):**
- `src/worker/worker/collectors/base_web_collector.py`
- `src/worker/worker/collectors/playwright_manager.py`
- `src/worker/worker/collectors/simple_web_collector.py`
- `src/worker/worker/collectors/rss_collector.py`
