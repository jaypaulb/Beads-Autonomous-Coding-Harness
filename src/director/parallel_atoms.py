"""
Parallel Execution Atoms - Pure Utility Functions
=================================================

Pure functions for parallel execution logic with zero dependencies.
These atoms support the ParallelMetrics class and parallel orchestration.
"""

from datetime import datetime
from typing import Any


# =============================================================================
# ATOMS - Pure functions with no dependencies
# =============================================================================


def sort_by_priority(issues: list[dict]) -> list[dict]:
    """
    Sort issues by Beads priority (P0-P4, lower number = higher priority).

    This atom sorts a list of issue dicts by their 'priority' key.
    Issues without priority are treated as lowest priority (priority 5).
    Original list is not modified; returns a new sorted list.

    Args:
        issues: List of issue dicts, each may have a 'priority' key (0-4)

    Returns:
        New list sorted by priority, highest priority (0) first

    Examples:
        >>> sort_by_priority([{'id': 'a', 'priority': 2}, {'id': 'b', 'priority': 0}])
        [{'id': 'b', 'priority': 0}, {'id': 'a', 'priority': 2}]

        >>> sort_by_priority([{'id': 'x'}])  # No priority = treated as 5
        [{'id': 'x'}]
    """
    # Use 5 as default for missing priority (lower than P4=3)
    # This ensures issues without priority sort last
    return sorted(issues, key=lambda issue: issue.get("priority", 5))


def recommend_parallelism(success_rate: float, current_parallel: int = 2) -> int:
    """
    Recommend max parallel count based on success rate.

    This atom implements the scaling logic for parallel execution:
    - Scale up (add 1) if success rate >= 90%
    - Scale down (subtract 1) if success rate < 70%
    - Maintain current level otherwise

    Bounds: minimum 1, maximum 4

    Args:
        success_rate: Success rate as float 0.0-1.0 (e.g., 0.85 = 85%)
        current_parallel: Current parallel count (default 2)

    Returns:
        Recommended max_parallel value (1-4)

    Examples:
        >>> recommend_parallelism(0.95, 2)  # High success, scale up
        3

        >>> recommend_parallelism(0.65, 3)  # Low success, scale down
        2

        >>> recommend_parallelism(0.80, 2)  # Medium success, maintain
        2
    """
    if success_rate >= 0.90:
        # High success rate - scale up
        new_parallel = current_parallel + 1
    elif success_rate < 0.70:
        # Low success rate - scale down
        new_parallel = current_parallel - 1
    else:
        # Acceptable success rate - maintain
        new_parallel = current_parallel

    # Enforce bounds: min 1, max 4
    return max(1, min(4, new_parallel))


def create_execution_record(
    parallel_count: int,
    conflicts: int,
    success: bool,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Create a dict record for ParallelMetrics storage.

    This atom creates a structured dict suitable for JSON serialization
    and storage in .beads/parallel_metrics.json.

    Args:
        parallel_count: Number of parallel agents that were executed
        conflicts: Number of merge conflicts that occurred
        success: Whether the parallel execution succeeded overall
        timestamp: Optional ISO format timestamp; if None, uses current time

    Returns:
        Dict with keys: timestamp, parallel_count, conflicts, success

    Examples:
        >>> record = create_execution_record(3, 0, True, "2025-01-15T10:30:00")
        >>> record['parallel_count']
        3
        >>> record['success']
        True
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    return {
        "timestamp": timestamp,
        "parallel_count": parallel_count,
        "conflicts": conflicts,
        "success": success,
    }


def calculate_success_rate(executions: list[dict], window: int = 10) -> float:
    """
    Calculate success rate from execution records.

    This atom calculates the success rate over the last N executions.
    Returns 0.0 if no executions exist.

    Args:
        executions: List of execution record dicts (each has 'success' key)
        window: Number of recent executions to consider (default 10)

    Returns:
        Success rate as float 0.0-1.0

    Examples:
        >>> calculate_success_rate([{'success': True}, {'success': True}, {'success': False}])
        0.6666666666666666
    """
    if not executions:
        return 0.0

    # Take only the last `window` executions
    recent = executions[-window:]

    if not recent:
        return 0.0

    successes = sum(1 for e in recent if e.get("success", False))
    return successes / len(recent)
