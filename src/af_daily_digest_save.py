import argparse
import os
from datetime import date, datetime

import pytz
from dotenv import load_dotenv

from ops_daily_digest import OperatorDailyDigest


parser = argparse.ArgumentParser()
parser.add_argument("--prefix", help="runtime prefix path",
                    default="./run")
parser.add_argument("--start", help="start time",
                    default=datetime.now().isoformat())
parser.add_argument("--run-id", help="run-id",
                    default="")
parser.add_argument("--job-id", help="job-id",
                    default="")
parser.add_argument("--data-folder", help="data folder to save",
                    default="data/daily_digest")
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="notion")


def load_data(args, op):
    """Load data from json file."""
    print("######################################################")
    print("# Load Daily Digest data from json")
    print("######################################################")
    pages = op.readFromJson(args.data_folder, args.run_id, "daily_digest.json")
    return pages


def generate_digest(args, op, pages):
    """Generate digest content using LLM."""
    print("######################################################")
    print("# Generate Daily Digest")
    print("######################################################")

    # Use current date in configured timezone for the title
    # This ensures the digest title matches when it's actually delivered (e.g., 6:00 AM SGT)
    tz_name = os.getenv("DAILY_DIGEST_TIMEZONE", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC
    today = datetime.now(tz).strftime("%Y-%m-%d")
    print(f"Using today's date in {tz_name}: {today}")

    categorized = op.categorize_pages(pages)
    digest = op.generate_digest(categorized, today=today)
    return digest


def publish(args, op, digest, targets):
    """Push digest to targets."""
    print("######################################################")
    print(f"# Publish Daily Digest to: {targets}")
    print("######################################################")
    op.push(digest, targets)


def run(args):
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")

    # Use current date in configured timezone for the title
    tz_name = os.getenv("DAILY_DIGEST_TIMEZONE", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC
    today = datetime.now(tz).strftime("%Y-%m-%d")

    print(f"Targets: {targets}, exec_date: {exec_date}, today: {today}, workdir: {workdir}")

    op = OperatorDailyDigest()
    pages = load_data(args, op)

    if not pages:
        print("[INFO] No pages to digest, creating empty digest")
        digest = {
            "title": f"Daily Digest - {today}",
            "content": "No significant news items found for this period.",
            "translation": "",
            "sources": {},
            "date": today,
        }
    else:
        digest = generate_digest(args, op, pages)

    publish(args, op, digest, targets)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
