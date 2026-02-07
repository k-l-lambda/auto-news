#!/usr/bin/env python3
"""
Auto-news Health Check and Auto-fix Script

This script checks the health of the auto-news pipeline and automatically
fixes common issues like:
- Notion schema overflow (creates new ToRead database)
- Consecutive push failures detection

Run this as a daily/hourly task or integrate into existing DAGs.
"""
import os
import re
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv

from notion import NotionAgent
from mysql_cli import MySQLClient
from ops_notion import OperatorNotion


class HealthChecker:
    def __init__(self):
        load_dotenv()
        self.notion_api_key = os.getenv("NOTION_TOKEN")
        self.notion_agent = NotionAgent(self.notion_api_key)
        self.issues = []
        self.actions = []

    def check_recent_push_failures(self, log_dir: str, hours: int = 6) -> dict:
        """
        Check recent logs for push failures.

        Returns:
            dict with 'total_runs', 'failed_runs', 'error_types'
        """
        print("=" * 60)
        print("Checking recent push failures...")
        print("=" * 60)

        cutoff_time = datetime.now() - timedelta(hours=hours)
        results = {
            "total_runs": 0,
            "failed_runs": 0,
            "zero_push_runs": 0,
            "error_types": {},
            "schema_overflow": False,
        }

        # Find recent save task logs
        pattern = os.path.join(log_dir, "dag_id=news_pulling/run_id=*/task_id=save/attempt=*.log")
        log_files = glob.glob(pattern)

        for log_file in log_files:
            # Check file modification time
            mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            if mtime < cutoff_time:
                continue

            results["total_runs"] += 1

            with open(log_file, 'r') as f:
                content = f.read()

            # Check for push failures
            failures = re.findall(r'\[ERROR\]: Push to notion failed.*?:(.*)', content)
            if failures:
                results["failed_runs"] += 1
                for failure in failures:
                    error_type = failure.strip()[:50]
                    results["error_types"][error_type] = results["error_types"].get(error_type, 0) + 1

                    # Check for schema overflow
                    if "database schema has exceeded" in failure.lower():
                        results["schema_overflow"] = True

            # Check for zero pushes (last total_pushed line)
            push_matches = re.findall(r'total_pushed: (\d+)', content)
            if push_matches:
                last_push = int(push_matches[-1])
                if last_push == 0:
                    results["zero_push_runs"] += 1

        print(f"Total runs checked: {results['total_runs']}")
        print(f"Runs with failures: {results['failed_runs']}")
        print(f"Runs with zero pushes: {results['zero_push_runs']}")
        print(f"Schema overflow detected: {results['schema_overflow']}")

        if results["error_types"]:
            print("Error types found:")
            for error, count in results["error_types"].items():
                print(f"  - {error}: {count}")

        return results

    def check_toread_database_health(self) -> dict:
        """
        Check if ToRead database is healthy by attempting a test query.

        Returns:
            dict with 'healthy', 'database_id', 'error'
        """
        print("=" * 60)
        print("Checking ToRead database health...")
        print("=" * 60)

        result = {
            "healthy": False,
            "database_id": None,
            "error": None,
        }

        try:
            op_notion = OperatorNotion()
            db_index_id = op_notion.get_index_toread_dbid()

            # Get current ToRead database ID
            from notion_client import Client
            notion = Client(auth=self.notion_api_key)

            # Query index to get latest ToRead database
            # Try different sort property names as Notion databases vary
            try:
                response = notion.databases.query(
                    database_id=db_index_id,
                    sorts=[{"timestamp": "created_time", "direction": "descending"}],
                    page_size=1
                )
            except Exception:
                # Fallback: query without sort
                response = notion.databases.query(
                    database_id=db_index_id,
                    page_size=10
                )

            if response["results"]:
                page = response["results"][0]
                db_id = page["properties"]["Name"]["title"][0]["text"]["content"]
                result["database_id"] = db_id

                # Try to query the ToRead database
                try:
                    notion.databases.query(database_id=db_id, page_size=1)
                    result["healthy"] = True
                    print(f"ToRead database {db_id} is healthy")
                except Exception as e:
                    result["error"] = str(e)
                    print(f"ToRead database {db_id} query failed: {e}")
            else:
                result["error"] = "No ToRead database found in index"
                print(result["error"])

        except Exception as e:
            result["error"] = str(e)
            print(f"Health check failed: {e}")

        return result

    def create_new_toread_database(self, month_name: str = None) -> str:
        """
        Create a new ToRead database.

        Returns:
            New database ID or None if failed
        """
        print("=" * 60)
        print("Creating new ToRead database...")
        print("=" * 60)

        try:
            db_cli = MySQLClient()
            indexes = db_cli.index_pages_table_load()
            notion_indexes = indexes.get("notion", {})

            toread_page_id = notion_indexes.get("toread_page_id", {}).get("index_id")
            index_toread_db_id = notion_indexes.get("index_toread_db_id", {}).get("index_id")

            if not toread_page_id or not index_toread_db_id:
                print("[ERROR] Missing toread_page_id or index_toread_db_id")
                return None

            if not month_name:
                month_name = datetime.now().strftime("%Y-%m")

            db_name = f"ToRead - {month_name}"
            print(f"Creating database: {db_name}")

            # Create the database
            toread_db = self.notion_agent.createDatabase_ToRead(db_name, toread_page_id)
            toread_db_id = toread_db["id"]
            print(f"Created database: {toread_db_id}")

            # Add to index
            from notion_client import Client
            notion = Client(auth=self.notion_api_key)

            properties = {
                "Name": {
                    "title": [{"text": {"content": toread_db_id}}]
                }
            }

            notion.pages.create(
                parent={"database_id": index_toread_db_id},
                properties=properties
            )
            print(f"Added to index database")

            self.actions.append(f"Created new ToRead database: {db_name} ({toread_db_id})")
            return toread_db_id

        except Exception as e:
            print(f"[ERROR] Failed to create ToRead database: {e}")
            return None

    def run_health_check(self, log_dir: str, auto_fix: bool = True) -> dict:
        """
        Run full health check and optionally auto-fix issues.

        Args:
            log_dir: Path to Airflow logs directory
            auto_fix: Whether to automatically fix detected issues

        Returns:
            Health check report dict
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": [],
            "actions": [],
            "status": "healthy",
        }

        # Check 1: Recent push failures
        push_results = self.check_recent_push_failures(log_dir)

        if push_results["schema_overflow"]:
            issue = "Notion database schema overflow detected"
            report["issues"].append(issue)
            report["status"] = "critical"

            if auto_fix:
                print("\n[AUTO-FIX] Creating new ToRead database...")
                new_db_id = self.create_new_toread_database()
                if new_db_id:
                    report["actions"].append(f"Created new ToRead database: {new_db_id}")
                else:
                    report["actions"].append("Failed to create new ToRead database")

        elif push_results["zero_push_runs"] >= 3:
            issue = f"Multiple runs ({push_results['zero_push_runs']}) with zero pushes"
            report["issues"].append(issue)
            report["status"] = "warning"

        # Check 2: ToRead database health
        db_health = self.check_toread_database_health()
        if not db_health["healthy"]:
            issue = f"ToRead database unhealthy: {db_health['error']}"
            report["issues"].append(issue)
            if report["status"] != "critical":
                report["status"] = "warning"

        # Print report
        print("\n" + "=" * 60)
        print("HEALTH CHECK REPORT")
        print("=" * 60)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Status: {report['status'].upper()}")

        if report["issues"]:
            print("\nIssues Found:")
            for issue in report["issues"]:
                print(f"  - {issue}")

        if report["actions"]:
            print("\nActions Taken:")
            for action in report["actions"]:
                print(f"  - {action}")

        if not report["issues"]:
            print("\nNo issues detected. System is healthy.")

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-news Health Check")
    parser.add_argument("--log-dir", default="/opt/airflow/logs",
                        help="Airflow logs directory")
    parser.add_argument("--no-auto-fix", action="store_true",
                        help="Disable auto-fix")
    parser.add_argument("--hours", type=int, default=6,
                        help="Hours of logs to check")

    args = parser.parse_args()

    checker = HealthChecker()
    report = checker.run_health_check(
        log_dir=args.log_dir,
        auto_fix=not args.no_auto_fix
    )

    # Exit with non-zero code if critical issues found
    if report["status"] == "critical":
        exit(1)


if __name__ == "__main__":
    main()
