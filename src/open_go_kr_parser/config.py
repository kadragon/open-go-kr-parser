# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0004
"""Configuration loader for agency settings."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Agency:
    """Represents a government agency to monitor."""

    code: str
    name: str


def load_agencies(config_path: Path) -> list[Agency]:
    """Load agency configuration from YAML file.

    Args:
        config_path: Path to the agencies.yaml file.

    Returns:
        List of Agency objects.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    agencies = []
    for item in data.get("agencies", []):
        agency = Agency(code=item["code"], name=item["name"])
        agencies.append(agency)

    return agencies
