"""
Progress Tracking Utilities
===========================

Functions for tracking and displaying progress of the autonomous coding agent.
Progress is tracked via Beads issues at the harness root level.
"""

import json
from pathlib import Path

from beads_config import BEADS_PROJECT_MARKER, BEADS_ROOT


def load_beads_project_state(project_dir: Path = None) -> dict | None:
    """
    Load the Beads project state from the marker file.

    Args:
        project_dir: Ignored - always uses BEADS_ROOT for single-database architecture

    Returns:
        Project state dict or None if not initialized
    """
    # Always check harness root for beads marker (single database architecture)
    marker_file = BEADS_ROOT / BEADS_PROJECT_MARKER

    if not marker_file.exists():
        return None

    try:
        with open(marker_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def is_beads_initialized(project_dir: Path = None) -> bool:
    """
    Check if Beads infrastructure is available at harness root.

    Args:
        project_dir: Ignored - always checks BEADS_ROOT

    Returns:
        True if .beads/ exists at harness root with valid marker
    """
    # Check for .beads directory at root
    beads_dir = BEADS_ROOT / ".beads"
    if not beads_dir.exists():
        return False

    # Check for marker file
    state = load_beads_project_state()
    return state is not None and state.get("initialized", False)


def is_spec_initialized(project_dir: Path) -> bool:
    """
    Check if a specific spec has been initialized (has issues created).

    Each spec creates its own .beads_project.json with the META issue ID
    when the initializer agent completes. This allows multiple specs to
    share the root-level beads database while tracking their own state.

    Args:
        project_dir: The spec directory to check

    Returns:
        True if this spec has been initialized (has .beads_project.json with meta_issue_id)
    """
    if project_dir is None:
        return False

    spec_marker = project_dir / BEADS_PROJECT_MARKER
    if not spec_marker.exists():
        return False

    try:
        with open(spec_marker, "r") as f:
            state = json.load(f)
            # A spec is initialized if it has a META issue ID
            return state.get("meta_issue_id") is not None
    except (json.JSONDecodeError, IOError):
        return False


def print_session_header(session_num: int, is_initializer: bool) -> None:
    """Print a formatted header for the session."""
    session_type = "INITIALIZER" if is_initializer else "CODING AGENT"

    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print("=" * 70)
    print()


def print_progress_summary(project_dir: Path = None) -> None:
    """
    Print a summary of current progress.

    Since actual progress is tracked in Beads at harness root, this reads
    the root state file for cached information. The agent updates Beads
    directly and reports progress in session comments.
    """
    state = load_beads_project_state()

    if state is None:
        print("\nProgress: Beads project not yet initialized")
        return

    total = state.get("total_issues", 0)
    meta_issue = state.get("meta_issue_id", "unknown")

    print(f"\nBeads Project Status:")
    print(f"  Total issues created: {total}")
    print(f"  META issue ID: {meta_issue}")
    print(f"  (Run 'bd info' for current issue counts)")
