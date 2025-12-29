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


def get_target_dates() -> list[str]:
    """Get target dates based on current weekday.

    - Monday: Previous Friday, Saturday, Sunday
    - Tuesday-Sunday: Yesterday only

    Returns:
        List of date strings in YYYY-MM-DD format.
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=Monday, 4=Friday

    if weekday == 0:  # Monday
        # Get previous Friday (3 days ago), Saturday (2 days ago), Sunday (1 day ago)
        dates = [
            today - timedelta(days=3),  # Friday
            today - timedelta(days=2),  # Saturday
            today - timedelta(days=1),  # Sunday
        ]
    else:
        # Tuesday-Sunday: just yesterday
        dates = [today - timedelta(days=1)]

    return [d.strftime("%Y-%m-%d") for d in dates]


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
        "--dates",
        type=str,
        default=None,
        help="Target dates (YYYY-MM-DD, comma-separated), defaults to auto-calculated",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to agencies.yaml config file",
    )
    args = parser.parse_args()

    # Get target dates
    if args.dates:
        target_dates = [d.strip() for d in args.dates.split(",")]
    else:
        target_dates = get_target_dates()
    logger.info(f"Fetching documents for dates: {target_dates}")

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

    # Process each agency for each target date
    has_errors = False
    for target_date in target_dates:
        logger.info(f"Processing date: {target_date}")

        for agency in agencies:
            logger.info(f"Processing agency: {agency.name} ({agency.code})")

            try:
                documents = api_client.fetch_documents(
                    agency.code, agency.name, target_date
                )
                logger.info(f"Found {len(documents)} documents for {agency.name}")

                notifier.send_documents(agency.name, target_date, documents)
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
