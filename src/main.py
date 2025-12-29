# Trace: spec_id=SPEC-scheduler-001 task_id=TASK-0005
"""Main entry point for the notification service."""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from client import OpenGoKrClient, OpenGoKrError
from config import load_agencies
from notifier import TelegramError, TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_target_date_range() -> tuple[str, str]:
    """Get target date range based on current weekday.

    - Monday: Previous Friday ~ Sunday (3 days)
    - Tuesday-Sunday: Yesterday only (1 day)

    Returns:
        Tuple of (start_date, end_date) strings in YYYY-MM-DD format.
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=Monday, 4=Friday

    if weekday == 0:  # Monday
        # Query from Friday (3 days ago) to Sunday (1 day ago)
        start_date = today - timedelta(days=3)  # Friday
        end_date = today - timedelta(days=1)  # Sunday
    else:
        # Tuesday-Sunday: just yesterday
        start_date = today - timedelta(days=1)
        end_date = start_date

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def find_config_path() -> Path:
    """Find the agencies.yaml config file.

    Returns:
        Path to the config file.

    Raises:
        FileNotFoundError: If config file not found.
    """
    # Check common locations
    candidates = [
        # Path relative to the script file (most reliable when running from source)
        Path(__file__).parent.parent / "config" / "agencies.yaml",
        # Path relative to current working directory
        Path("config/agencies.yaml"),
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError("agencies.yaml not found. Expected in config/agencies.yaml")


def main() -> int:
    """Run the notification service.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        description="Fetch and notify about government document disclosures"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD), defaults to auto-calculated",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD), defaults to start-date if not specified",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to agencies.yaml config file",
    )
    args = parser.parse_args()

    # Get target date range
    if args.start_date:
        start_date = args.start_date
        end_date = args.end_date if args.end_date else start_date
    else:
        start_date, end_date = get_target_date_range()

    if start_date == end_date:
        logger.info(f"Fetching documents for date: {start_date}")
        date_display = start_date
    else:
        logger.info(f"Fetching documents for date range: {start_date} ~ {end_date}")
        date_display = f"{start_date} ~ {end_date}"

    # Load configuration
    try:
        config_path = Path(args.config) if args.config else find_config_path()
        agencies = load_agencies(config_path)
        logger.info(f"Loaded {len(agencies)} agencies from config")
    except FileNotFoundError as e:
        logger.error(f"Config error: {e}")
        return 1

    if not agencies:
        logger.warning("No agencies configured")
        return 0

    # Get Telegram credentials from environment
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.error(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables"
        )
        return 1

    # Initialize clients
    api_client = OpenGoKrClient()
    notifier = TelegramNotifier(bot_token, chat_id)

    # Process each agency with date range (single API call per agency)
    has_errors = False
    for agency in agencies:
        logger.info(f"Processing agency: {agency.name} ({agency.code})")

        try:
            documents = api_client.fetch_documents(
                agency.code, agency.name, start_date, end_date
            )
            logger.info(f"Found {len(documents)} documents for {agency.name}")

            notifier.send_documents(agency.name, date_display, documents)
            logger.info(f"Notification sent for {agency.name}")

        except OpenGoKrError as e:
            logger.error(f"API error for {agency.name}: {e}")
            has_errors = True
            continue

        except TelegramError as e:
            logger.error(f"Telegram error for {agency.name}: {e}")
            has_errors = True
            continue

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
