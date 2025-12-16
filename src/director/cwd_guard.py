"""
CWD Guard - Working Directory Safety
=====================================

Molecules for working directory validation and protection.
These compose atoms from utils.py to provide cohesive cwd safety.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from src.director.utils import resolve_absolute_path

# Configure module logger
logger = logging.getLogger(__name__)


class WorkingDirectoryGuard:
    """
    Context manager that validates and protects the working directory.

    This molecule composes the resolve_absolute_path atom with cwd management
    to ensure working directory consistency during critical operations.

    Usage:
        with WorkingDirectoryGuard(expected_cwd):
            # operations that must maintain cwd
            ...
        # cwd is restored if changed during context

    On __enter__:
        - Asserts current cwd matches expected_cwd
        - Raises RuntimeError if mismatch
        - Saves original cwd for restoration

    On __exit__:
        - Restores cwd if it changed during context
        - Logs cwd at entry and exit for debugging
    """

    def __init__(self, expected_cwd: Path):
        """
        Initialize the guard with the expected working directory.

        Args:
            expected_cwd: The directory that cwd MUST be when entering context
        """
        self._expected_cwd = resolve_absolute_path(expected_cwd)
        self._original_cwd: Optional[Path] = None

    def __enter__(self) -> "WorkingDirectoryGuard":
        """
        Enter the context, validating cwd matches expected.

        Raises:
            RuntimeError: If current cwd does not match expected_cwd
        """
        actual_cwd = resolve_absolute_path(Path.cwd())
        self._original_cwd = actual_cwd

        logger.debug(f"WorkingDirectoryGuard: entering with cwd={actual_cwd}")

        if actual_cwd != self._expected_cwd:
            raise RuntimeError(
                f"Working directory mismatch on context entry. "
                f"Expected: {self._expected_cwd}, Actual: {actual_cwd}"
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context, restoring cwd if it changed.

        Always restores cwd to what it was on entry, regardless of exceptions.
        """
        current_cwd = resolve_absolute_path(Path.cwd())

        logger.debug(f"WorkingDirectoryGuard: exiting with cwd={current_cwd}")

        if self._original_cwd is not None and current_cwd != self._original_cwd:
            logger.warning(
                f"WorkingDirectoryGuard: cwd changed during context. "
                f"Restoring from {current_cwd} to {self._original_cwd}"
            )
            os.chdir(self._original_cwd)

        logger.debug(f"WorkingDirectoryGuard: cwd after exit={Path.cwd().resolve()}")


def validate_cwd(expected: Path) -> None:
    """
    Validate that current working directory matches expected.

    This molecule composes the resolve_absolute_path atom with cwd checking
    for standalone pre-command validation.

    Args:
        expected: The expected current working directory

    Raises:
        RuntimeError: If actual cwd does not match expected, with clear
                     error message showing both actual and expected paths

    Example:
        validate_cwd(project_root)  # Raises if cwd != project_root
        run_my_command()  # Safe to proceed
    """
    expected_resolved = resolve_absolute_path(expected)
    actual_cwd = resolve_absolute_path(Path.cwd())

    if actual_cwd != expected_resolved:
        raise RuntimeError(
            f"Working directory validation failed. "
            f"Expected: {expected_resolved}, Actual: {actual_cwd}"
        )
