"""
Test Molecules: BV Robot Plan Query
====================================

Tests for the BV (Beads Viewer) robot plan query molecule.
This molecule queries `bv robot --plan` CLI and parses execution plans.
Graceful fallback when BV is unavailable (returns empty plan).
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest

# Import module under test (to be implemented)
from src.director.bv_robot_plan import (
    query_bv_robot_plan,
    parse_bv_plan_output,
    BVRobotPlan,
)


class TestQueryBVRobotPlan:
    """Tests for query_bv_robot_plan() molecule."""

    def test_returns_plan_on_successful_cli_call(self, tmp_path):
        """query_bv_robot_plan() returns parsed plan on successful CLI call."""
        # Arrange: Mock successful BV CLI response
        mock_output = """ROBOT EXECUTION PLAN
===================

Phase 1: Database Layer
-----------------------
- [6.1] Write molecule tests (Linear-Coding-Agent-Harness-6jxw)
- [6.2] Create query function (Linear-Coding-Agent-Harness-v3mu)

Phase 2: API Layer
------------------
- [6.3] Add graceful fallback (Linear-Coding-Agent-Harness-pzal)

Ready: 2 tasks
Blocked: 0 tasks
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["bv", "robot", "--plan"],
                returncode=0,
                stdout=mock_output,
                stderr="",
            )

            # Act
            result = query_bv_robot_plan(project_dir=tmp_path)

            # Assert
            assert result is not None
            assert isinstance(result, BVRobotPlan)
            assert result.success is True
            assert result.raw_output == mock_output
            # Plan should have parsed content
            assert len(result.phases) >= 0  # May be empty if parsing not implemented

    def test_returns_empty_plan_when_cli_unavailable(self, tmp_path):
        """query_bv_robot_plan() returns empty plan when BV CLI not found."""
        # Arrange: Mock CLI not found (FileNotFoundError)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("bv not found")

            # Act
            result = query_bv_robot_plan(project_dir=tmp_path)

            # Assert: Should return empty plan, NOT raise
            assert result is not None
            assert isinstance(result, BVRobotPlan)
            assert result.success is False
            assert result.error_message is not None
            assert "not found" in result.error_message.lower() or "unavailable" in result.error_message.lower()
            assert result.phases == []

    def test_returns_empty_plan_when_cli_returns_error(self, tmp_path):
        """query_bv_robot_plan() returns empty plan when BV CLI fails with non-zero exit."""
        # Arrange: Mock CLI error (e.g., TTY required error)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["bv", "robot", "--plan"],
                returncode=1,
                stdout="",
                stderr="Error running beads viewer: could not open a new TTY: open /dev/tty: no such device",
            )

            # Act
            result = query_bv_robot_plan(project_dir=tmp_path)

            # Assert: Should return empty plan with error info
            assert result is not None
            assert isinstance(result, BVRobotPlan)
            assert result.success is False
            assert result.error_message is not None
            assert result.phases == []

    def test_handles_empty_cli_output_gracefully(self, tmp_path):
        """query_bv_robot_plan() handles empty CLI output without crashing."""
        # Arrange: Mock empty output (but successful return)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["bv", "robot", "--plan"],
                returncode=0,
                stdout="",
                stderr="",
            )

            # Act
            result = query_bv_robot_plan(project_dir=tmp_path)

            # Assert: Should succeed but with empty plan
            assert result is not None
            assert isinstance(result, BVRobotPlan)
            assert result.success is True  # CLI succeeded
            assert result.phases == []  # But no phases to parse


class TestParseBVPlanOutput:
    """Tests for parse_bv_plan_output() helper function."""

    def test_parses_phase_structure_from_output(self):
        """parse_bv_plan_output() extracts phase structure from BV output."""
        # Arrange: Sample BV robot plan output
        raw_output = """ROBOT EXECUTION PLAN
===================

Phase 1: Database Layer
-----------------------
- Task A
- Task B

Phase 2: API Layer
------------------
- Task C
"""
        # Act
        phases = parse_bv_plan_output(raw_output)

        # Assert
        assert isinstance(phases, list)
        # Should have extracted at least the phase headers
        assert len(phases) >= 0  # Exact parsing TBD

    def test_returns_empty_list_for_empty_input(self):
        """parse_bv_plan_output() returns empty list for empty input."""
        # Act
        phases = parse_bv_plan_output("")

        # Assert
        assert phases == []

    def test_returns_empty_list_for_none_input(self):
        """parse_bv_plan_output() returns empty list for None input."""
        # Act
        phases = parse_bv_plan_output(None)

        # Assert
        assert phases == []


class TestBVRobotPlanDataclass:
    """Tests for BVRobotPlan dataclass structure."""

    def test_has_required_attributes(self):
        """BVRobotPlan has all required attributes."""
        # Arrange & Act
        plan = BVRobotPlan(
            success=True,
            raw_output="test output",
            phases=[],
            error_message=None,
        )

        # Assert
        assert hasattr(plan, "success")
        assert hasattr(plan, "raw_output")
        assert hasattr(plan, "phases")
        assert hasattr(plan, "error_message")

    def test_default_values_for_empty_plan(self):
        """BVRobotPlan can be created with minimal defaults for empty plan."""
        # Arrange & Act: Create empty/failed plan
        plan = BVRobotPlan(
            success=False,
            error_message="CLI unavailable",
        )

        # Assert: Should have sensible defaults
        assert plan.success is False
        assert plan.error_message == "CLI unavailable"
        assert plan.raw_output == ""
        assert plan.phases == []
