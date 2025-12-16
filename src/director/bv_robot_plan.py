"""
BV Robot Plan Molecules
=======================

Molecules for querying the BV (Beads Viewer) robot execution plan.
Provides graceful fallback when BV CLI is unavailable.

The `bv robot --plan` command outputs an execution plan for the robot mode,
showing phases and tasks in dependency order. This module queries that plan
and parses the output for use by the Director.
"""

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Configure module logger
logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class BVRobotPlan:
    """
    Represents a BV robot execution plan query result.

    This dataclass holds both the raw CLI output and parsed structure,
    with graceful handling of failures (success=False, error_message set).

    Attributes:
        success: Whether the CLI query succeeded
        raw_output: Raw stdout from bv robot --plan (empty string if failed)
        phases: List of parsed phase dictionaries (empty if failed or unparseable)
        error_message: Human-readable error description (None if success)
    """

    success: bool
    raw_output: str = ""
    phases: List[dict] = field(default_factory=list)
    error_message: Optional[str] = None


# =============================================================================
# ATOMS - Pure parsing functions
# =============================================================================


def parse_bv_plan_output(raw_output: Optional[str]) -> List[dict]:
    """
    Parse raw BV robot plan output into structured phases.

    This atom extracts phase information from the BV robot --plan output.
    Returns empty list for None, empty string, or unparseable input.

    Args:
        raw_output: Raw stdout from bv robot --plan command

    Returns:
        List of phase dictionaries, each with 'name' and 'tasks' keys.
        Returns empty list if input is None, empty, or cannot be parsed.

    Example output structure:
        [
            {"name": "Phase 1: Database Layer", "tasks": ["Task A", "Task B"]},
            {"name": "Phase 2: API Layer", "tasks": ["Task C"]},
        ]
    """
    if raw_output is None or raw_output.strip() == "":
        return []

    phases = []
    current_phase = None

    # Pattern to match phase headers like "Phase 1: Database Layer"
    phase_pattern = re.compile(r"^(Phase\s+\d+:.*?)$", re.IGNORECASE | re.MULTILINE)
    # Pattern to match task lines starting with "- "
    task_pattern = re.compile(r"^\s*-\s+(.+)$")

    lines = raw_output.split("\n")

    for line in lines:
        # Check for phase header
        phase_match = phase_pattern.match(line.strip())
        if phase_match:
            # Save previous phase if exists
            if current_phase is not None:
                phases.append(current_phase)
            # Start new phase
            current_phase = {
                "name": phase_match.group(1).strip(),
                "tasks": [],
            }
            continue

        # Check for task line (only if we're in a phase)
        if current_phase is not None:
            task_match = task_pattern.match(line)
            if task_match:
                current_phase["tasks"].append(task_match.group(1).strip())

    # Don't forget the last phase
    if current_phase is not None:
        phases.append(current_phase)

    return phases


# =============================================================================
# MOLECULES - Composed query functions
# =============================================================================


def query_bv_robot_plan(
    project_dir: Optional[Path] = None,
    bv_executable: str = "bv",
    timeout_seconds: int = 30,
) -> BVRobotPlan:
    """
    Query the BV robot execution plan with graceful fallback.

    This molecule calls `bv robot --plan` and parses the output.
    Provides graceful fallback when BV is unavailable or fails:
    - Returns BVRobotPlan with success=False and helpful error_message
    - Never raises exceptions for expected failure modes

    Args:
        project_dir: Project directory for context (not used as cwd, for future use)
        bv_executable: Name or path to BV executable (default: "bv")
        timeout_seconds: Timeout for CLI call in seconds (default: 30)

    Returns:
        BVRobotPlan with success=True and parsed phases on success,
        or success=False with error_message on failure.

    Example:
        plan = query_bv_robot_plan()
        if plan.success:
            for phase in plan.phases:
                print(f"Phase: {phase['name']}")
        else:
            print(f"Could not get plan: {plan.error_message}")
    """
    # Check if BV executable exists
    bv_path = shutil.which(bv_executable)
    if bv_path is None:
        logger.warning(f"BV executable '{bv_executable}' not found in PATH")
        return BVRobotPlan(
            success=False,
            error_message=f"BV CLI unavailable: '{bv_executable}' not found in PATH",
        )

    # Build command
    cmd = [bv_path, "robot", "--plan"]
    logger.debug(f"Querying BV robot plan: {' '.join(cmd)}")

    try:
        # Execute BV CLI (NO cwd parameter - forbidden pattern)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        # Check for non-zero exit code
        if result.returncode != 0:
            error_detail = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            logger.warning(f"BV robot --plan failed with exit code {result.returncode}: {error_detail}")
            return BVRobotPlan(
                success=False,
                raw_output=result.stdout,
                error_message=f"BV CLI failed (exit {result.returncode}): {error_detail}",
            )

        # Success - parse the output
        raw_output = result.stdout
        phases = parse_bv_plan_output(raw_output)

        logger.debug(f"BV robot plan query successful, found {len(phases)} phases")
        return BVRobotPlan(
            success=True,
            raw_output=raw_output,
            phases=phases,
            error_message=None,
        )

    except FileNotFoundError as e:
        # BV executable not found (different from shutil.which check)
        logger.warning(f"BV executable not found: {e}")
        return BVRobotPlan(
            success=False,
            error_message=f"BV CLI unavailable: executable not found",
        )

    except subprocess.TimeoutExpired:
        logger.warning(f"BV robot --plan timed out after {timeout_seconds}s")
        return BVRobotPlan(
            success=False,
            error_message=f"BV CLI timed out after {timeout_seconds} seconds",
        )

    except subprocess.SubprocessError as e:
        logger.warning(f"BV subprocess error: {e}")
        return BVRobotPlan(
            success=False,
            error_message=f"BV CLI subprocess error: {str(e)}",
        )

    except Exception as e:
        # Catch-all for unexpected errors (log at error level)
        logger.error(f"Unexpected error querying BV robot plan: {e}", exc_info=True)
        return BVRobotPlan(
            success=False,
            error_message=f"Unexpected error: {str(e)}",
        )
