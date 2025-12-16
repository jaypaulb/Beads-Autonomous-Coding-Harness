"""
Director Module
===============

Utilities for the Project Development Director including path handling,
command execution, working directory safety, async timeout handling,
and git conflict resolution.
"""

from .utils import (
    resolve_absolute_path,
    validate_path_is_absolute,
    get_harness_root,
    format_command_for_logging,
)

from .timeout_atoms import (
    DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    VERIFICATION_TIMEOUT_SECONDS,
    CLI_QUERY_TIMEOUT_SECONDS,
    CLEANUP_GRACE_PERIOD_SECONDS,
)

from .timeout_organisms import (
    run_with_timeout,
    run_with_timeout_and_cancel,
    TimeoutError,
    TimeoutResult,
)

from .conflict_handler import (
    MergeStatus,
    MergeResult,
    attempt_automatic_merge,
    detect_merge_conflicts,
)

__all__ = [
    # Path utilities
    "resolve_absolute_path",
    "validate_path_is_absolute",
    "get_harness_root",
    "format_command_for_logging",
    # Timeout constants (atoms)
    "DEFAULT_SUBAGENT_TIMEOUT_SECONDS",
    "VERIFICATION_TIMEOUT_SECONDS",
    "CLI_QUERY_TIMEOUT_SECONDS",
    "CLEANUP_GRACE_PERIOD_SECONDS",
    # Timeout handling (organisms)
    "run_with_timeout",
    "run_with_timeout_and_cancel",
    "TimeoutError",
    "TimeoutResult",
    # Conflict handling (molecules)
    "MergeStatus",
    "MergeResult",
    "attempt_automatic_merge",
    "detect_merge_conflicts",
]
