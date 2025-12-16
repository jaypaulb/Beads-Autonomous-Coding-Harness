"""
Parallel Molecules - Git State Snapshot Functions
==================================================

Molecules for capturing and managing git state during parallel execution.
These compose atoms from utils.py to provide git snapshot functionality.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List

from src.director.utils import resolve_absolute_path, format_command_for_logging

# Configure module logger
logger = logging.getLogger(__name__)


class GitSnapshotError(Exception):
    """Raised when git snapshot operations fail."""

    pass


def _parse_porcelain_output(porcelain_output: str) -> List[str]:
    """
    Parse git status --porcelain output into a list of modified files.

    This is an internal helper that extracts file paths from porcelain format.
    Porcelain format: XY filename (where XY is two status characters).

    Args:
        porcelain_output: Raw output from git status --porcelain

    Returns:
        List of file paths that have modifications
    """
    if not porcelain_output.strip():
        return []

    modified_files = []
    # Split on newlines but preserve leading characters (status codes)
    # DO NOT strip the whole output as that removes leading space status chars
    for line in porcelain_output.rstrip("\n").split("\n"):
        if line:
            # Porcelain format: XY filename
            # First 2 chars are status codes, then a space, then filename
            # e.g., " M src/file.py" or "?? new_file.py"
            if len(line) > 3:
                filename = line[3:].strip()
                # Handle renamed files: "R  old -> new"
                if " -> " in filename:
                    filename = filename.split(" -> ")[-1]
                modified_files.append(filename)

    return modified_files


def snapshot_file_tree(project_dir: Path) -> Dict[str, any]:
    """
    Capture a snapshot of the git state for rollback reference.

    This molecule composes atoms to provide a complete git state snapshot:
    - Uses resolve_absolute_path() for path normalization
    - Uses format_command_for_logging() for debug output
    - Executes git commands to capture state

    The snapshot is used before spawning parallel agents to enable
    rollback if merge conflicts occur.

    Args:
        project_dir: Root directory of the git repository

    Returns:
        Dict containing:
        - git_status: Raw output from git status --porcelain
        - head_commit: Current HEAD SHA (40 character hash)
        - modified_files: List of file paths with modifications

    Raises:
        GitSnapshotError: If git commands fail (not a git repo, git not installed, etc.)
    """
    # Resolve to absolute path using atom
    project_dir_resolved = resolve_absolute_path(project_dir)

    # Verify the directory exists
    if not project_dir_resolved.exists():
        raise GitSnapshotError(f"Project directory does not exist: {project_dir_resolved}")

    if not project_dir_resolved.is_dir():
        raise GitSnapshotError(f"Project path is not a directory: {project_dir_resolved}")

    # Build git status command
    status_cmd = ["git", "-C", str(project_dir_resolved), "status", "--porcelain"]
    logger.debug(f"Executing: {format_command_for_logging(status_cmd)}")

    try:
        status_result = subprocess.run(
            status_cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero, we'll check ourselves
        )
    except FileNotFoundError:
        raise GitSnapshotError("git command not found - is git installed?")

    if status_result.returncode != 0:
        raise GitSnapshotError(
            f"git status failed: {status_result.stderr.strip()}"
        )

    git_status = status_result.stdout

    # Build git rev-parse HEAD command
    head_cmd = ["git", "-C", str(project_dir_resolved), "rev-parse", "HEAD"]
    logger.debug(f"Executing: {format_command_for_logging(head_cmd)}")

    try:
        head_result = subprocess.run(
            head_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise GitSnapshotError("git command not found - is git installed?")

    if head_result.returncode != 0:
        raise GitSnapshotError(
            f"git rev-parse HEAD failed: {head_result.stderr.strip()}"
        )

    head_commit = head_result.stdout.strip()

    # Parse modified files from porcelain output
    modified_files = _parse_porcelain_output(git_status)

    return {
        "git_status": git_status,
        "head_commit": head_commit,
        "modified_files": modified_files,
    }
