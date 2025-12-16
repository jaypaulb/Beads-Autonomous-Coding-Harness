"""
Director Improvement Tracker Organism - Execution Metrics Analysis
==================================================================

Organism for tracking sub-agent execution metrics and providing
recommendations for parallelism optimization. Composes metrics
molecules into higher-level tracking and analysis capabilities.

The tracker provides:
- Recording of execution metrics (duration, status, agent type)
- Success rate calculation with filtering
- Parallelism recommendations based on load and success rate
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .metrics_molecules import MetricsData, append_metrics, load_metrics
from .utils import get_harness_root

# Configure module logger
logger = logging.getLogger(__name__)

# Default metrics file location
DEFAULT_METRICS_FILE = get_harness_root() / ".director" / "metrics.json"


# =============================================================================
# ORGANISM - Improvement Tracker Functions
# =============================================================================


def record_execution(
    issue_id: str,
    agent_type: str,
    start_time: datetime,
    end_time: datetime,
    status: str,
    metrics_file: Optional[Path] = None,
) -> bool:
    """
    Record a sub-agent execution to the metrics file.

    This organism function creates a MetricsData entry from execution
    parameters and appends it to the metrics persistence store.

    Args:
        issue_id: The Beads issue ID that was worked on
        agent_type: Type of agent (e.g., atom-writer, molecule-composer)
        start_time: When execution started
        end_time: When execution completed
        status: Outcome status (success, failure, timeout, etc.)
        metrics_file: Optional custom path for metrics file

    Returns:
        True if recording succeeded, False on failure
    """
    if metrics_file is None:
        metrics_file = DEFAULT_METRICS_FILE

    # Calculate duration in seconds
    duration = (end_time - start_time).total_seconds()

    # Create metrics entry
    metrics = MetricsData(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        duration=duration,
        status=status,
        agent_type=agent_type,
        issue_id=issue_id,
    )

    # Append to metrics file
    success = append_metrics(metrics, metrics_file)

    if success:
        logger.info(
            f"Recorded execution: issue={issue_id}, agent={agent_type}, "
            f"duration={duration:.1f}s, status={status}"
        )
    else:
        logger.error(f"Failed to record execution for issue {issue_id}")

    return success


def get_success_rate(
    agent_type: Optional[str] = None,
    time_window_hours: Optional[float] = None,
    metrics_file: Optional[Path] = None,
) -> Optional[float]:
    """
    Calculate success rate from recorded metrics.

    This organism function loads metrics data and calculates the ratio
    of successful executions to total executions, with optional filtering
    by agent type and time window.

    Args:
        agent_type: Optional filter for specific agent type
        time_window_hours: Optional filter for recent metrics (hours from now)
        metrics_file: Optional custom path for metrics file

    Returns:
        Float between 0.0 and 1.0 representing success rate,
        or None if no data matches the filters
    """
    if metrics_file is None:
        metrics_file = DEFAULT_METRICS_FILE

    # Load all metrics
    metrics_list = load_metrics(metrics_file)

    if metrics_list is None or len(metrics_list) == 0:
        logger.debug("No metrics data available for success rate calculation")
        return None

    # Apply time window filter if specified
    if time_window_hours is not None:
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        filtered_by_time = []
        for m in metrics_list:
            try:
                entry_time = datetime.fromisoformat(m.start_time)
                if entry_time >= cutoff_time:
                    filtered_by_time.append(m)
            except ValueError as e:
                logger.warning(f"Invalid timestamp format in metrics: {m.start_time}, {e}")
                continue
        metrics_list = filtered_by_time

    # Apply agent type filter if specified
    if agent_type is not None:
        metrics_list = [m for m in metrics_list if m.agent_type == agent_type]

    # Calculate success rate
    if len(metrics_list) == 0:
        logger.debug(
            f"No metrics match filters: agent_type={agent_type}, "
            f"time_window_hours={time_window_hours}"
        )
        return None

    successful = sum(1 for m in metrics_list if m.status == "success")
    total = len(metrics_list)
    rate = successful / total

    logger.debug(
        f"Success rate: {rate:.2%} ({successful}/{total}) "
        f"[agent_type={agent_type}, time_window={time_window_hours}h]"
    )

    return rate


def recommend_parallelism(current_load: int, success_rate: float) -> int:
    """
    Recommend optimal number of parallel agents based on current metrics.

    This organism function analyzes current load and success rate to
    suggest adjusting parallelism up or down. The recommendation aims
    to maximize throughput while maintaining quality.

    Args:
        current_load: Current number of parallel agents running
        success_rate: Current success rate (0.0 to 1.0)

    Returns:
        Recommended number of parallel agents (1 to 5)

    Logic:
        - If success_rate > 0.8 and load < 3: increase by 1 (room to grow)
        - If success_rate < 0.5: decrease by 1 (struggling, reduce load)
        - Otherwise: maintain current load (stable performance)
    """
    # Clamp success_rate to valid range
    success_rate = max(0.0, min(1.0, success_rate))

    # Determine recommendation
    if success_rate > 0.8 and current_load < 3:
        # High success rate with low load - can increase
        recommended = current_load + 1
        logger.debug(
            f"Recommending increase: success_rate={success_rate:.2%} > 80%, "
            f"load={current_load} < 3 -> {recommended}"
        )
    elif success_rate < 0.5:
        # Low success rate - reduce load
        recommended = max(1, current_load - 1)
        logger.debug(
            f"Recommending decrease: success_rate={success_rate:.2%} < 50% "
            f"-> {recommended}"
        )
    else:
        # Maintain current load
        recommended = current_load
        logger.debug(
            f"Recommending maintain: success_rate={success_rate:.2%}, "
            f"load={current_load} -> {recommended}"
        )

    # Clamp to valid range (1-5)
    recommended = max(1, min(5, recommended))

    return recommended
