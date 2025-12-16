"""
Director Utilities - Path Atoms and Command Molecules
======================================================

Pure utility functions for path resolution and validation (atoms),
plus composed helpers for command execution (molecules).
"""

import logging
import subprocess
from pathlib import Path
from typing import List

# Configure module logger
logger = logging.getLogger(__name__)


# =============================================================================
# ATOMS - Pure functions with no dependencies
# =============================================================================


def resolve_absolute_path(path: Path | str) -> Path:
    """
    Resolve a path to its absolute, canonical form.

    This atom converts any path (relative or absolute, string or Path)
    to an absolute Path with all symlinks resolved.

    Args:
        path: A path as string or Path object

    Returns:
        Resolved absolute Path
    """
    if isinstance(path, str):
        path = Path(path)
    return path.resolve()


def validate_path_is_absolute(path: Path) -> bool:
    """
    Check if a path is absolute.

    This atom validates that a path starts from root (/).
    It does not check if the path exists.

    Args:
        path: Path to validate

    Returns:
        True if path is absolute, False otherwise
    """
    return path.is_absolute()


def get_harness_root() -> Path:
    """
    Get the resolved harness root directory.

    This atom returns the root directory of the Linear-Coding-Agent-Harness
    project. It matches the BEADS_ROOT constant from beads_config.py.

    Returns:
        Absolute resolved path to harness root
    """
    # Navigate from this file to the harness root
    # This file is at: src/director/utils.py
    # Harness root is 3 levels up: src/director/ -> src/ -> harness/
    return Path(__file__).parent.parent.parent.resolve()


def format_command_for_logging(cmd: list) -> str:
    """
    Format a command list for human-readable debug output.

    This atom takes a command list (as used by subprocess.run)
    and formats it as a string suitable for logging. Arguments
    containing spaces are quoted.

    Args:
        cmd: List of command arguments

    Returns:
        Formatted command string
    """
    if not cmd:
        return ""

    formatted_parts = []
    for part in cmd:
        # Quote arguments that contain spaces
        if " " in str(part):
            formatted_parts.append(f'"{part}"')
        else:
            formatted_parts.append(str(part))

    return " ".join(formatted_parts)


# =============================================================================
# MOLECULES - Composed helpers using atoms
# =============================================================================


def run_command(
    cmd: List[str], project_dir: Path, **kwargs
) -> subprocess.CompletedProcess:
    """
    Execute a command with absolute paths, NO cwd parameter.

    This molecule composes atoms to safely execute shell commands:
    - Uses resolve_absolute_path() to make all paths absolute
    - Uses format_command_for_logging() for debug output
    - NEVER uses the cwd= parameter (forbidden pattern)

    Args:
        cmd: Command and arguments as a list (first element is executable)
        project_dir: Base directory for resolving relative path arguments
        **kwargs: Additional arguments passed to subprocess.run
                  (except 'cwd' which is explicitly forbidden)

    Returns:
        subprocess.CompletedProcess from the command execution

    Raises:
        ValueError: If 'cwd' is passed in kwargs (forbidden pattern)

    Example:
        # Instead of: subprocess.run(["pytest", "tests"], cwd="/project")
        # Use: run_command(["pytest", "tests"], Path("/project"))
        # This converts to: subprocess.run(["pytest", "/project/tests"])
    """
    # Explicitly forbid the cwd parameter
    if "cwd" in kwargs:
        raise ValueError(
            "The 'cwd' parameter is forbidden. "
            "Use absolute paths in command arguments instead."
        )

    # Resolve project_dir to absolute
    project_dir_resolved = resolve_absolute_path(project_dir)

    # Build command with absolute paths
    # First element is the executable, remaining are arguments
    absolute_cmd = [cmd[0]] if cmd else []

    for arg in cmd[1:]:
        # Check if arg looks like a path (contains / or is a relative path)
        # Heuristic: if it doesn't start with - (not a flag) and could be a path
        if not arg.startswith("-") and ("/" in arg or not arg.startswith("-")):
            # Try to resolve as path relative to project_dir
            potential_path = project_dir_resolved / arg
            if potential_path.exists() or "/" in arg:
                # Use the absolute path
                absolute_cmd.append(str(resolve_absolute_path(potential_path)))
            else:
                # Not a path, keep as-is
                absolute_cmd.append(arg)
        else:
            # Flags and other arguments pass through unchanged
            absolute_cmd.append(arg)

    # Log the full command for debugging
    formatted_cmd = format_command_for_logging(absolute_cmd)
    logger.debug(f"Executing command: {formatted_cmd}")

    # Execute without cwd parameter
    return subprocess.run(absolute_cmd, **kwargs)
