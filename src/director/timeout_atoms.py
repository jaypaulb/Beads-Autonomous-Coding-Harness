"""
Timeout Atoms - Pure Constants and Configuration
=================================================

Pure constants for timeout handling. These atoms define timeout values
used throughout the sub-agent spawning system.

No dependencies, no side effects - just configuration values.
"""

# =============================================================================
# ATOMS - Timeout Constants
# =============================================================================

# Default timeout for sub-agent execution (10 minutes)
# Sub-agents working on tasks should complete within this window.
# If a sub-agent exceeds this timeout, it will be cancelled and
# the task will be marked for retry or escalation.
DEFAULT_SUBAGENT_TIMEOUT_SECONDS: int = 600

# Shorter timeout for simple verification operations
# Used for quick checks like verifying issue status
VERIFICATION_TIMEOUT_SECONDS: int = 30

# Timeout for issue loading from Beads CLI
# Should be quick - CLI queries shouldn't take long
CLI_QUERY_TIMEOUT_SECONDS: int = 10

# Grace period for cleanup after timeout (seconds)
# How long to wait for graceful shutdown before force cancel
CLEANUP_GRACE_PERIOD_SECONDS: float = 5.0
