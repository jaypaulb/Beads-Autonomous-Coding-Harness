"""
Director Conflict Handler - Git Merge Conflict Molecules
=========================================================

Molecules for handling git merge operations and detecting conflicts.
These compose git command atoms into cohesive merge handling units.
"""

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .utils import resolve_absolute_path, format_command_for_logging

# Configure module logger
logger = logging.getLogger(__name__)


# =============================================================================
# ATOMS - Enums and Data Classes
# =============================================================================


class MergeStatus(Enum):
    """Status of a merge operation attempt."""

    MERGED = "merged"  # Merge completed successfully
    CONFLICT = "conflict"  # Merge has conflicts that need resolution
    ERROR = "error"  # Git error (not a conflict, e.g., branch not found)


@dataclass
class MergeResult:
    """Result of a merge operation attempt.

    Attributes:
        status: The outcome status of the merge operation
        error_message: Error or conflict details if status is not MERGED
        conflicted_files: List of files with conflicts (if any)
    """

    status: MergeStatus
    error_message: Optional[str] = None
    conflicted_files: Optional[List[str]] = None


# =============================================================================
# MOLECULES - Composed helpers for merge operations
# =============================================================================


def attempt_automatic_merge(
    branch_name: str,
    project_dir: Path,
) -> MergeResult:
    """
    Attempt to automatically merge a branch into the current branch.

    This molecule executes a git merge and analyzes the result to determine
    if it succeeded, encountered conflicts, or failed with an error.

    Args:
        branch_name: Name of the branch to merge
        project_dir: Absolute path to the git repository

    Returns:
        MergeResult with status indicating outcome:
        - MERGED: Clean merge, no conflicts
        - CONFLICT: Merge has conflicts requiring manual resolution
        - ERROR: Git error (branch not found, not a repo, etc.)
    """
    project_dir_resolved = resolve_absolute_path(project_dir)

    # Build git merge command
    cmd = ["git", "-C", str(project_dir_resolved), "merge", branch_name]

    logger.debug(f"Attempting merge: {format_command_for_logging(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Analyze the result
        if result.returncode == 0:
            # Clean merge
            logger.info(f"Successfully merged branch '{branch_name}'")
            return MergeResult(status=MergeStatus.MERGED)

        # Check if this is a conflict vs other error
        combined_output = f"{result.stdout}\n{result.stderr}".lower()

        if "conflict" in combined_output:
            # Merge conflict detected
            conflict_files = detect_merge_conflicts(project_dir_resolved)
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.warning(f"Merge conflict detected: {error_msg}")
            return MergeResult(
                status=MergeStatus.CONFLICT,
                error_message=error_msg,
                conflicted_files=conflict_files,
            )

        # Other git error (branch not found, etc.)
        error_msg = result.stderr.strip() or result.stdout.strip()
        logger.error(f"Git merge error: {error_msg}")
        return MergeResult(
            status=MergeStatus.ERROR,
            error_message=error_msg,
        )

    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error during merge: {e}")
        return MergeResult(
            status=MergeStatus.ERROR,
            error_message=str(e),
        )


def detect_merge_conflicts(project_dir: Path) -> List[str]:
    """
    Detect files with merge conflicts in a git repository.

    This molecule queries git for unmerged files (files with conflicts)
    and returns their paths.

    Args:
        project_dir: Absolute path to the git repository

    Returns:
        List of file paths (relative to repo root) that have conflicts.
        Returns empty list if no conflicts or on error.
    """
    project_dir_resolved = resolve_absolute_path(project_dir)

    # Use git diff with --diff-filter=U to find unmerged (conflicted) files
    cmd = [
        "git",
        "-C",
        str(project_dir_resolved),
        "diff",
        "--name-only",
        "--diff-filter=U",
    ]

    logger.debug(f"Detecting conflicts: {format_command_for_logging(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.warning(f"Git diff command failed: {result.stderr}")
            return []

        # Parse output - one file per line
        stdout = result.stdout.strip()
        if not stdout:
            return []

        conflicted_files = [line.strip() for line in stdout.split("\n") if line.strip()]
        logger.debug(f"Found {len(conflicted_files)} conflicted files")
        return conflicted_files

    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error detecting conflicts: {e}")
        return []
