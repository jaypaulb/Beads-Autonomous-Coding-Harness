"""
Director Metrics Molecules - Execution Metrics Persistence
===========================================================

Molecules for persisting and loading sub-agent execution metrics.
These compose JSON I/O atoms into cohesive metrics handling units.

The metrics system tracks:
- Execution timing (start, end, duration)
- Agent type and issue assignment
- Success/failure status
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .utils import resolve_absolute_path

# Configure module logger
logger = logging.getLogger(__name__)


# =============================================================================
# ATOMS - Data Classes
# =============================================================================


@dataclass
class MetricsData:
    """
    Data class for storing sub-agent execution metrics.

    Attributes:
        start_time: ISO format timestamp when execution started
        end_time: ISO format timestamp when execution completed
        duration: Execution duration in seconds
        status: Outcome status (success, failure, timeout, etc.)
        agent_type: Type of agent that executed (e.g., atom-writer, molecule-composer)
        issue_id: Beads issue ID that was being worked on
    """

    start_time: str
    end_time: str
    duration: float
    status: str
    agent_type: str
    issue_id: str


# =============================================================================
# MOLECULES - Composed helpers for metrics persistence
# =============================================================================


def save_metrics(metrics_list: List[MetricsData], file_path: Path) -> bool:
    """
    Save a list of metrics entries to a JSON file.

    This molecule writes metrics data to disk in JSON format. It overwrites
    any existing file at the target path.

    Args:
        metrics_list: List of MetricsData entries to save
        file_path: Absolute path to the JSON file to write

    Returns:
        True if save succeeded, False on error
    """
    file_path_resolved = resolve_absolute_path(file_path)

    try:
        # Ensure parent directory exists
        file_path_resolved.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dicts for JSON serialization
        data = [asdict(m) for m in metrics_list]

        with open(file_path_resolved, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved {len(metrics_list)} metrics entries to {file_path_resolved}")
        return True

    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Failed to save metrics to {file_path_resolved}: {e}")
        return False


def load_metrics(file_path: Path) -> Optional[List[MetricsData]]:
    """
    Load metrics entries from a JSON file.

    This molecule reads metrics data from disk and reconstructs MetricsData
    objects. Returns None if the file doesn't exist or contains invalid data.

    Args:
        file_path: Absolute path to the JSON file to read

    Returns:
        List of MetricsData entries, or None if file missing or invalid
    """
    file_path_resolved = resolve_absolute_path(file_path)

    if not file_path_resolved.exists():
        logger.debug(f"Metrics file not found: {file_path_resolved}")
        return None

    try:
        with open(file_path_resolved, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error(f"Invalid metrics format: expected list, got {type(data)}")
            return None

        # Reconstruct MetricsData objects from dicts
        metrics_list = []
        for entry in data:
            if not isinstance(entry, dict):
                logger.warning(f"Skipping invalid metrics entry: {entry}")
                continue

            try:
                metrics = MetricsData(
                    start_time=entry["start_time"],
                    end_time=entry["end_time"],
                    duration=entry["duration"],
                    status=entry["status"],
                    agent_type=entry["agent_type"],
                    issue_id=entry["issue_id"],
                )
                metrics_list.append(metrics)
            except KeyError as e:
                logger.warning(f"Skipping metrics entry missing field: {e}")
                continue

        logger.debug(f"Loaded {len(metrics_list)} metrics entries from {file_path_resolved}")
        return metrics_list

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metrics file {file_path_resolved}: {e}")
        return None
    except (OSError, TypeError) as e:
        logger.error(f"Failed to load metrics from {file_path_resolved}: {e}")
        return None


def append_metrics(metrics: MetricsData, file_path: Path) -> bool:
    """
    Append a single metrics entry to an existing file.

    This molecule loads existing metrics (if any), adds the new entry,
    and saves the combined list. If the file doesn't exist, it creates
    a new file with just this entry.

    Args:
        metrics: Single MetricsData entry to append
        file_path: Absolute path to the JSON file

    Returns:
        True if append succeeded, False on error
    """
    file_path_resolved = resolve_absolute_path(file_path)

    # Load existing metrics (or start with empty list if file doesn't exist)
    existing = load_metrics(file_path_resolved)
    if existing is None:
        existing = []

    # Append the new entry
    existing.append(metrics)

    # Save the combined list
    success = save_metrics(existing, file_path_resolved)

    if success:
        logger.debug(f"Appended metrics entry for issue {metrics.issue_id}")

    return success
