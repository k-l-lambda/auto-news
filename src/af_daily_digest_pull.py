import argparse
import os
from datetime import datetime

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
parser.add_argument("--sources", help="sources to pull, comma separated",
                    default="Article,RSS,Twitter,Reddit,Youtube")
parser.add_argument("--hours-back", help="hours to look back",
                    type=int, default=24)
parser.add_argument("--min-rating", help="minimum rating to include",
                    type=int, default=3)


def pull(args, op, sources, hours_back):
    """Pull ToRead items from last N hours."""
    print("######################################################")
    print("# Pull Daily Digest Items")
    print("######################################################")
    data = op.pull(sources=sources, hours_back=hours_back)
    return data


def filter_items(args, op, data, min_rating):
    """Filter items by rating."""
    print("######################################################")
    print("# Filter Items by Rating")
    print("######################################################")
    filtered = op.filter_by_interests(data, min_rating=min_rating)
    return filtered


def save(args, op, data):
    """Save the middle result (json) to data folder."""
    print("######################################################")
    print("# Save Daily Digest data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "daily_digest.json", data)


def run(args):
    # Get sources from args or environment
    sources_str = args.sources or os.getenv("DAILY_DIGEST_SOURCES", "Article,RSS,Twitter,Reddit,Youtube")
    sources = sources_str.split(",")

    # Get hours_back from args or environment
    hours_back = args.hours_back or int(os.getenv("DAILY_DIGEST_HOURS_BACK", 24))

    # Get min_rating from args or environment
    min_rating = args.min_rating or int(os.getenv("DAILY_DIGEST_MIN_RATING", 3))

    print(f"Sources: {sources}")
    print(f"Hours back: {hours_back}")
    print(f"Min rating: {min_rating}")

    op = OperatorDailyDigest()
    data = pull(args, op, sources, hours_back)
    filtered_data = filter_items(args, op, data, min_rating)
    save(args, op, filtered_data)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
