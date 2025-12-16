"""
Beads Configuration
====================

Configuration constants for Beads integration.
These values are used in prompts and for project state management.
"""

import os
from pathlib import Path

# Harness root directory - where beads_config.py lives
# This is the Linear-Coding-Agent-Harness directory
HARNESS_ROOT = Path(__file__).parent.resolve()

# Beads root directory - where .beads/ database lives
# Currently same as HARNESS_ROOT. Can be overridden via BEADS_ROOT environment variable
# to support multi-project setups where .beads/ is at a parent level.
BEADS_ROOT = Path(os.environ.get("BEADS_ROOT", HARNESS_ROOT))

# ================================================
# PATH CONSTANTS FOR DIRECTORY STRUCTURE
# ================================================

# Product documentation directory
# Contains mission.md, roadmap.md, tech-stack.md
PRODUCT_DOCS_DIR = HARNESS_ROOT / "agent-os" / "product"

# Specs directory
# Contains dated spec folders like 2025-12-16-architectural-fixes/
SPECS_DIR = HARNESS_ROOT / "agent-os" / "specs"

# Director prompts directory
# Contains director_prompt.md and related prompts
DIRECTOR_PROMPTS_DIR = HARNESS_ROOT / "prompts"

# Default number of issues to create (can be overridden via command line)
DEFAULT_ISSUE_COUNT = 50

# Issue status workflow (Beads states)
STATUS_TODO = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "closed"

# Issue types
TYPE_FEATURE = "feature"
TYPE_BUG = "bug"
TYPE_TASK = "task"

# Label categories (map to feature types)
LABEL_FUNCTIONAL = "functional"
LABEL_STYLE = "style"
LABEL_INFRASTRUCTURE = "infrastructure"

# Priority mapping (Beads uses 0-4 where 0=Urgent, 4=Low)
PRIORITY_URGENT = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

# Local marker file to track Beads project initialization
BEADS_PROJECT_MARKER = ".beads_project.json"

# Meta issue title for project tracking and session handoff
META_ISSUE_TITLE = "[META] Project Progress Tracker"

# ================================================
# BEADS VIEWER (BV) CONFIGURATION
# ================================================

# Enable Beads Viewer graph intelligence features
# BV provides execution planning, graph insights, cycle detection
BV_ENABLED = True

# Fall back to basic bd commands if BV is not available
# This ensures graceful degradation without hard failures
BV_FALLBACK_ENABLED = True


# ================================================
# BEADS LOCATION VALIDATION
# ================================================

def validate_beads_location() -> bool:
    """
    Validate that .beads/ exists only at BEADS_ROOT, not in spec directories.

    This is a pure function that checks for the single-database architecture.
    Returns True if the architecture is correct (no spec-level .beads/).
    Returns False if any spec-level .beads/ directories are detected.

    Returns:
        True if .beads/ location is valid, False if rogue directories exist
    """
    # Import here to avoid circular dependency
    from progress import detect_rogue_beads_dirs

    rogue_dirs = detect_rogue_beads_dirs()
    return len(rogue_dirs) == 0
