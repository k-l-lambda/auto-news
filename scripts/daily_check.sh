#!/bin/bash
# Auto-news Daily Health Check Script
# Runs at 06:30 local time to check and fix auto-news pipeline issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/daily_check.local.md"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)

# Ensure PATH includes node/claude
export PATH="/home/camus/.nvm/versions/node/v21.7.1/bin:$PATH"

# Prompt for the daily check agent
PROMPT=$(cat <<'EOF'
You are an auto-news pipeline health check agent. Your task is to independently check AND FIX issues in the auto-news system.

## Your Responsibilities

1. **Check DAG Status**
   - Check recent `news_pulling` DAG runs (last 24 hours)
   - Check recent `sync_dist` DAG runs (last 24 hours)
   - Check `daily_digest` DAG status
   - Identify any failed or stuck tasks

2. **Check Service Health**
   - Verify Milvus is accessible (test connection)
   - Check Docker containers are running (airflow, milvus, redis, mysql)
   - Check disk space usage

3. **Check Notion Push Results** (CRITICAL - check ACTUAL errors, not just stats)
   - **IMPORTANT**: `total_pushed` in logs shows items ATTEMPTED, not SUCCEEDED
   - Search for ACTUAL push errors: `grep "Push to notion failed" <log_file>`
   - Check for schema overflow: `grep "database schema has exceeded" <log_file>`
   - If you find "database schema has exceeded the maximum size" errors:
     - This is a CRITICAL issue - ALL pushes are failing silently
     - The `total_pushed` stat will still show a number, but nothing actually pushed
     - FIX: Create a new ToRead database (see Fix section below)
   - Check the processing pipeline stats: total_input → post_deduping → post_scoring → post_filtering → post_summary → post_ranking → total_pushed
   - Common causes of push failures:
     - **Schema overflow** (most critical) → create new ToRead database
     - LLM score threshold too high (check `After LLM score filter` in logs)
     - All articles have `__relevant_score: -1` (cold start, no historical data)
     - Milvus connection issues during scoring

4. **Diagnose Issues**
   - For failed tasks, read the task logs to identify root cause
   - **ALWAYS check for Notion API errors** - they don't cause DAG failure!
   - Common issues:
     - **Notion schema overflow** → CRITICAL, create new ToRead database
     - Milvus connection timeout → usually transient, retry helps
     - LLM API timeout → check API availability
     - OOM errors → check container memory limits
     - Import errors → check code deployment
     - LLM score filter too strict → adjust threshold in af_save.py

5. **Fix Issues PROACTIVELY**
   - Retry failed DAG runs if the issue seems transient
   - Trigger manual DAG runs if scheduled runs were missed
   - **Fix Notion Schema Overflow** (when you see "database schema has exceeded"):
     ```bash
     # Create new ToRead database for current month
     sudo docker exec docker-airflow-worker-1 bash -c "cd /opt/airflow/run/auto-news/src && python create_toread_db.py"
     ```
     Then trigger a new DAG run to verify pushes work.
   - If code changes are needed:
     1. Edit the source file in `/home/camus/work/auto-news/src/`
     2. Copy to docker workspace: `cp src/FILE.py docker/workspace/airflow/run/auto-news/src/`
     3. Trigger a new DAG run to verify the fix
   - Use this command to trigger DAGs:
     ```bash
     sudo docker exec docker-airflow-scheduler-1 bash -c "export PYTHONPATH=/home/airflow/.local/lib/python3.11/site-packages; /usr/local/bin/python /home/airflow/.local/bin/airflow dags trigger <dag_name>"
     ```

6. **Verify Fixes**
   - After triggering a fix, wait for the task to complete
   - Check the logs to confirm the issue is resolved
   - If total_pushed > 0, the fix worked

7. **Report Results**
   - Write a summary to daily_check.local.md with:
     - Date and time of check
     - Status of each DAG (success/failed/issues found)
     - Processing pipeline stats (how many articles at each stage)
     - Actions taken to fix issues
     - Verification results (did the fix work?)
     - Any unresolved issues that need manual intervention
   - Format as markdown with clear sections

## Key Paths

- Airflow logs: `/home/camus/work/auto-news/docker/workspace/airflow/logs/`
- DAG definitions: `/home/camus/work/auto-news/dags/`
- Source code: `/home/camus/work/auto-news/src/`
- Docker workspace code: `/home/camus/work/auto-news/docker/workspace/airflow/run/auto-news/src/`

## Key Log Patterns to Search

```bash
# CRITICAL: Check for Notion push errors (do this FIRST!)
grep "Push to notion failed" <log_file>
grep "database schema has exceeded" <log_file>

# Check push stats (but remember: this is ATTEMPTED, not SUCCEEDED)
grep "total_pushed" <log_file>

# Check LLM score filter
grep "After LLM score filter" <log_file>

# Check processing pipeline
grep -E "total_input|post_deduping|post_scoring|post_filtering|post_summary|post_ranking" <log_file>

# Check relevant scores
grep "__relevant_score" <log_file> | head -10
```

## CRITICAL: Schema Overflow Detection

If you see errors like:
```
[ERROR]: Push to notion failed, skip: Your database schema has exceeded the maximum size.
```

This means:
1. The ToRead database has too many unique values in multi_select fields
2. ALL pushes are failing, even though DAG shows "success"
3. The `total_pushed` stat is MISLEADING - it shows attempted, not succeeded

**Immediate fix:**
```bash
sudo docker exec docker-airflow-worker-1 bash -c "cd /opt/airflow/run/auto-news/src && python create_toread_db.py"
```

## Important Notes

- BE PROACTIVE: Don't just report issues, FIX THEM
- **ALWAYS check for Notion API errors** - they are silent failures!
- If total_pushed is 0, this is a CRITICAL issue - investigate and fix
- If you see "schema has exceeded" errors, create new ToRead database IMMEDIATELY
- Always verify your fix worked before reporting success
- If you fix something, commit the change: `cd /home/camus/work/auto-news && git add -A && git commit -m "Fix: description"`
- If an issue requires human intervention, clearly mark it as **NEEDS ATTENTION**
- The daily_check.local.md file should append new entries, not overwrite

You have a password to run sudo commands: `ppio`

Start by checking the current date and time, then proceed with the health check. Remember: your goal is a WORKING pipeline that pushes content to Notion.
EOF
)

# Create log entry header
echo "" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
echo "## Daily Check: $DATE $TIME" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Run claude using claude.local.sh
cd "$PROJECT_DIR"
"$PROJECT_DIR/claude.local.sh" --print --output-format text -p "$PROMPT" 2>&1 | tee -a "$LOG_FILE"

echo "" >> "$LOG_FILE"
echo "_Check completed at $(date +%H:%M:%S)_" >> "$LOG_FILE"
