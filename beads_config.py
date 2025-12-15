"""
Beads Configuration
====================

Configuration constants for Beads integration.
These values are used in prompts and for project state management.
"""

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
