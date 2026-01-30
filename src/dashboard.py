"""
Dashboard - System status and database statistics
"""

import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Airflow API config
AIRFLOW_HOST = os.getenv("AIRFLOW_HOST", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "airflow")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")


def get_airflow_dags():
    """Get all DAGs status from Airflow."""
    try:
        resp = requests.get(
            f"{AIRFLOW_HOST}/api/v1/dags",
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("dags", [])
    except Exception as e:
        print(f"Error fetching DAGs: {e}")
    return []


def get_dag_runs(dag_id, limit=5):
    """Get recent runs for a DAG."""
    try:
        resp = requests.get(
            f"{AIRFLOW_HOST}/api/v1/dags/{dag_id}/dagRuns",
            params={"order_by": "-execution_date", "limit": limit},
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("dag_runs", [])
    except Exception as e:
        print(f"Error fetching runs for {dag_id}: {e}")
    return []


def trigger_dag(dag_id):
    """Trigger a DAG run via Airflow API."""
    try:
        resp = requests.post(
            f"{AIRFLOW_HOST}/api/v1/dags/{dag_id}/dagRuns",
            json={"conf": {}},
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
            timeout=10
        )
        if resp.status_code in [200, 201]:
            return {"success": True, "data": resp.json()}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_notion_stats():
    """Get Notion database statistics."""
    try:
        from notion import NotionAgent
        from ops_notion import OperatorNotion
        import utils

        notion_api_key = os.getenv("NOTION_TOKEN")
        if not notion_api_key:
            return {"error": "NOTION_TOKEN not set"}

        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # Get ToRead database index
        db_index_id = op_notion.get_index_toread_dbid()
        db_pages = utils.get_notion_database_pages_toread(notion_agent, db_index_id)

        stats = {
            "toread_databases": len(db_pages),
            "databases": []
        }

        # Get stats for each database (limit to 2 most recent)
        for db_page in db_pages[:2]:
            db_id = db_page["database_id"]
            db_info = {
                "id": db_id,
                "created": db_page.get("created_time", "")[:10],
                "sources": {}
            }

            # Count by source
            for source in ["Web", "RSS", "Article", "Twitter", "Reddit", "Youtube"]:
                try:
                    pages = notion_agent.queryDatabaseToRead(
                        db_id, source,
                        extraction_interval=0,
                        require_user_rating=False
                    )
                    db_info["sources"][source] = len(pages)
                except Exception:
                    db_info["sources"][source] = 0

            stats["databases"].append(db_info)

        return stats

    except Exception as e:
        return {"error": str(e)}


def get_mysql_stats():
    """Get MySQL database statistics."""
    try:
        from db_cli import DBClient
        db = DBClient()

        stats = {
            "indexes": len(db.indexes.get("notion", {})),
            "index_keys": list(db.indexes.get("notion", {}).keys())
        }
        return stats
    except Exception as e:
        return {"error": str(e)}


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Auto-News Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0; padding: 20px;
        }
        h1 { color: #38bdf8; margin-bottom: 20px; }
        h2 { color: #94a3b8; margin: 20px 0 10px; font-size: 1.2em; }
        .container { max-width: 1200px; margin: 0 auto; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card {
            background: #1e293b; border-radius: 12px; padding: 20px;
            border: 1px solid #334155;
        }
        .card h3 { color: #38bdf8; margin-bottom: 15px; font-size: 1.1em; }
        .stat { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; }
        .stat:last-child { border-bottom: none; }
        .stat-label { color: #94a3b8; }
        .stat-value { font-weight: 600; }
        .success { color: #4ade80; }
        .failed { color: #f87171; }
        .running { color: #fbbf24; }
        .paused { color: #94a3b8; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; font-weight: 500; }
        .badge {
            padding: 2px 8px; border-radius: 4px; font-size: 0.85em;
        }
        .badge-success { background: #166534; color: #4ade80; }
        .badge-failed { background: #7f1d1d; color: #f87171; }
        .badge-running { background: #854d0e; color: #fbbf24; }
        .refresh {
            position: fixed; top: 20px; right: 20px;
            background: #3b82f6; color: white; border: none;
            padding: 10px 20px; border-radius: 8px; cursor: pointer;
        }
        .refresh:hover { background: #2563eb; }
        .timestamp { color: #64748b; font-size: 0.9em; margin-top: 20px; }
        .trigger-btn {
            background: #059669; color: white; border: none;
            padding: 6px 12px; border-radius: 6px; cursor: pointer;
            font-size: 0.85em; margin-top: 10px; width: 100%;
        }
        .trigger-btn:hover { background: #047857; }
        .trigger-btn:disabled { background: #475569; cursor: not-allowed; }
        .trigger-btn.loading { background: #854d0e; }
        .toast {
            position: fixed; bottom: 20px; right: 20px;
            background: #1e293b; border: 1px solid #334155;
            padding: 12px 20px; border-radius: 8px;
            display: none; z-index: 1000;
        }
        .toast.success { border-color: #4ade80; }
        .toast.error { border-color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Auto-News Dashboard</h1>
        <button class="refresh" onclick="location.reload()">🔄 Refresh</button>

        <h2>Airflow DAGs</h2>
        <div class="grid">
            {% for dag in dags %}
            <div class="card">
                <h3>{{ dag.dag_id }}</h3>
                <div class="stat">
                    <span class="stat-label">Status</span>
                    <span class="stat-value {% if dag.is_paused %}paused{% else %}success{% endif %}">
                        {{ 'Paused' if dag.is_paused else 'Active' }}
                    </span>
                </div>
                <div class="stat">
                    <span class="stat-label">Schedule</span>
                    <span class="stat-value">{{ dag.schedule_interval.value if dag.schedule_interval else 'Manual' }}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Next Run</span>
                    <span class="stat-value">{{ dag.next_dagrun[:16] if dag.next_dagrun else 'N/A' }}</span>
                </div>
                {% if dag.runs %}
                <h4 style="margin-top: 15px; color: #94a3b8; font-size: 0.9em;">Recent Runs</h4>
                {% for run in dag.runs[:3] %}
                <div class="stat">
                    <span class="stat-label">{{ run.execution_date[:16] }}</span>
                    <span class="badge badge-{{ run.state }}">{{ run.state }}</span>
                </div>
                {% endfor %}
                {% endif %}
                <button class="trigger-btn" onclick="triggerDag('{{ dag.dag_id }}', this)">
                    ▶ Trigger Run
                </button>
            </div>
            {% endfor %}
        </div>

        <h2>Database Statistics</h2>
        <div class="grid">
            <div class="card">
                <h3>MySQL Indexes</h3>
                <div class="stat">
                    <span class="stat-label">Total Indexes</span>
                    <span class="stat-value">{{ mysql_stats.indexes if mysql_stats.indexes else 'N/A' }}</span>
                </div>
                {% if mysql_stats.index_keys %}
                {% for key in mysql_stats.index_keys %}
                <div class="stat">
                    <span class="stat-label">{{ key }}</span>
                    <span class="stat-value success">✓</span>
                </div>
                {% endfor %}
                {% endif %}
            </div>

            {% if notion_stats.databases %}
            {% for db in notion_stats.databases %}
            <div class="card">
                <h3>ToRead {{ db.created }}</h3>
                {% for source, count in db.sources.items() %}
                <div class="stat">
                    <span class="stat-label">{{ source }}</span>
                    <span class="stat-value">{{ count }}</span>
                </div>
                {% endfor %}
            </div>
            {% endfor %}
            {% endif %}
        </div>

        <p class="timestamp">Last updated: {{ timestamp }}</p>
    </div>

    <div id="toast" class="toast"></div>

    <script>
    function showToast(message, type) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = 'toast ' + type;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }

    async function triggerDag(dagId, btn) {
        btn.disabled = true;
        btn.classList.add('loading');
        btn.textContent = '⏳ Triggering...';

        try {
            const resp = await fetch('/api/trigger/' + dagId, { method: 'POST' });
            const data = await resp.json();

            if (data.success) {
                showToast('✓ ' + dagId + ' triggered successfully!', 'success');
                btn.textContent = '✓ Triggered!';
                setTimeout(() => location.reload(), 2000);
            } else {
                showToast('✗ Failed: ' + data.error, 'error');
                btn.textContent = '▶ Trigger Run';
                btn.disabled = false;
                btn.classList.remove('loading');
            }
        } catch (e) {
            showToast('✗ Error: ' + e.message, 'error');
            btn.textContent = '▶ Trigger Run';
            btn.disabled = false;
            btn.classList.remove('loading');
        }
    }
    </script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """Main dashboard page."""
    # Get Airflow DAGs
    dags = get_airflow_dags()

    # Add recent runs to each DAG
    for dag in dags:
        dag["runs"] = get_dag_runs(dag["dag_id"], limit=3)

    # Filter to important DAGs
    important_dags = ["news_pulling", "daily_digest", "action", "journal_daily", "collection_weekly"]
    dags = [d for d in dags if d["dag_id"] in important_dags]

    # Get database stats
    mysql_stats = get_mysql_stats()

    # Skip Notion stats for now (too slow for dashboard)
    notion_stats = {"databases": []}

    return render_template_string(
        DASHBOARD_HTML,
        dags=dags,
        mysql_stats=mysql_stats,
        notion_stats=notion_stats,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@app.route("/api/stats")
def api_stats():
    """API endpoint for stats."""
    dags = get_airflow_dags()
    for dag in dags:
        dag["runs"] = get_dag_runs(dag["dag_id"], limit=5)

    return {
        "dags": dags,
        "mysql": get_mysql_stats(),
        "timestamp": datetime.now().isoformat()
    }


@app.route("/api/trigger/<dag_id>", methods=["POST"])
def api_trigger_dag(dag_id):
    """Trigger a DAG run."""
    result = trigger_dag(dag_id)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    print(f"Starting dashboard on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
