"""
Progress Tracking Utilities
===========================

Functions for tracking and displaying progress of the autonomous coding agent.
Progress is tracked via Beads issues at the project root level.
"""

import json
from pathlib import Path

from beads_config import BEADS_PROJECT_MARKER, BEADS_ROOT, SPECS_DIR


def load_beads_project_state(project_dir: Path = None) -> dict | None:
    """
    Load the Beads project state from the marker file.

    Args:
        project_dir: Ignored - always uses BEADS_ROOT for single-database architecture

    Returns:
        Project state dict or None if not initialized
    """
    # Always check project root for beads marker (single database architecture)
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
    Check if Beads infrastructure is available at project root.

    Args:
        project_dir: Ignored - always checks BEADS_ROOT

    Returns:
        True if .beads/ exists at project root with valid marker
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


def detect_rogue_beads_dirs() -> list[Path]:
    """
    Detect any .beads/ directories inside spec folders.

    This is a pure scan function that finds violations of the single-database
    architecture. Beads should only exist at BEADS_ROOT, not inside individual
    spec directories.

    Returns:
        List of Path objects pointing to violating .beads/ directories.
        Empty list if architecture is correct.
    """
    rogue_dirs = []

    # Only scan if SPECS_DIR exists
    if not SPECS_DIR.exists():
        return rogue_dirs

    # Walk through all spec directories looking for .beads/
    for spec_dir in SPECS_DIR.iterdir():
        if not spec_dir.is_dir():
            continue

        # Check for .beads/ at spec level
        potential_rogue = spec_dir / ".beads"
        if potential_rogue.exists() and potential_rogue.is_dir():
            rogue_dirs.append(potential_rogue)

        # Also check nested directories (e.g., spec/implementation/.beads)
        for subdir in spec_dir.rglob(".beads"):
            if subdir.is_dir() and subdir not in rogue_dirs:
                rogue_dirs.append(subdir)

    return rogue_dirs


def enforce_single_beads_database() -> None:
    """
    Enforce the single-database architecture by failing if rogue .beads/ exist.

    This validation function should be called at startup of director sessions
    to ensure no spec-level .beads/ directories have been created.

    Raises:
        RuntimeError: If any spec-level .beads/ directories are detected,
                     with a message listing all violating paths.
    """
    rogue_dirs = detect_rogue_beads_dirs()

    if rogue_dirs:
        paths_str = "\n  - ".join(str(p) for p in rogue_dirs)
        raise RuntimeError(
            f"Single-database architecture violation detected!\n"
            f"Found {len(rogue_dirs)} spec-level .beads/ directories:\n"
            f"  - {paths_str}\n\n"
            f"Run scripts/migrate_beads.py to consolidate to root database."
        )


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

    Since actual progress is tracked in Beads at project root, this reads
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
