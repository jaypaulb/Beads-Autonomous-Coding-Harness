"""
Test Orchestration: Parallel Execution Integration
===================================================

Organism-level integration tests for parallel execution infrastructure.
Tests verify how complete feature units work across layers (2-8 tests).

Test requirements from spec:
- Test parallel spawning with asyncio.TaskGroup
- Test snapshot_file_tree() capturing git state
- Test attempt_automatic_merge() success and failure paths
- Test handle_parallel_conflicts() priority-based rollback
- Test ParallelMetrics recording and recommendations
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Import from root src/director which has the parallel execution atoms/molecules
from src.director.parallel_molecules import (
    snapshot_file_tree,
    GitSnapshotError,
)
from src.director.parallel_atoms import (
    sort_by_priority,
    recommend_parallelism,
    create_execution_record,
    calculate_success_rate,
)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


class IssueStatusVerificationHelper:
    """
    Helper for verifying issue status after parallel operations.

    Tracks issue state transitions and provides assertions for
    verifying rollback behavior in conflict handling tests.

    Usage:
        helper = IssueStatusVerificationHelper()
        helper.record_status("bd-1", "in_progress")
        helper.record_status("bd-1", "done")
        assert helper.verify_transition("bd-1", "in_progress", "done")
    """

    def __init__(self):
        self.issues: Dict[str, List[str]] = {}
        self.comments: Dict[str, List[str]] = {}

    def record_status(self, issue_id: str, status: str) -> None:
        """Record a status change for an issue."""
        if issue_id not in self.issues:
            self.issues[issue_id] = []
        self.issues[issue_id].append(status)

    def record_comment(self, issue_id: str, comment: str) -> None:
        """Record a comment added to an issue."""
        if issue_id not in self.comments:
            self.comments[issue_id] = []
        self.comments[issue_id].append(comment)

    def get_status(self, issue_id: str) -> Optional[str]:
        """Get the current (latest) status of an issue."""
        if issue_id not in self.issues or not self.issues[issue_id]:
            return None
        return self.issues[issue_id][-1]

    def get_status_history(self, issue_id: str) -> List[str]:
        """Get the full status history for an issue."""
        return self.issues.get(issue_id, [])

    def verify_transition(self, issue_id: str, from_status: str, to_status: str) -> bool:
        """Verify that a specific status transition occurred."""
        history = self.get_status_history(issue_id)
        for i in range(len(history) - 1):
            if history[i] == from_status and history[i + 1] == to_status:
                return True
        return False

    def verify_was_rolled_back(self, issue_id: str) -> bool:
        """Verify that an issue was rolled back (reopened with comment)."""
        # Check if issue was reopened (status changed back to in_progress)
        history = self.get_status_history(issue_id)
        was_reopened = "in_progress" in history[1:] if len(history) > 1 else False

        # Check if rollback comment was added
        comments = self.comments.get(issue_id, [])
        has_rollback_comment = any("rollback" in c.lower() or "conflict" in c.lower() for c in comments)

        return was_reopened or has_rollback_comment

    def verify_no_rollback(self, issue_id: str) -> bool:
        """Verify that an issue was NOT rolled back."""
        return not self.verify_was_rolled_back(issue_id)


def create_issue_status_helper() -> IssueStatusVerificationHelper:
    """
    Factory function to create an issue status verification helper.

    Returns:
        IssueStatusVerificationHelper instance for tracking issue states.
    """
    return IssueStatusVerificationHelper()


@pytest.fixture
def issue_helper() -> IssueStatusVerificationHelper:
    """Pytest fixture for issue status verification."""
    return create_issue_status_helper()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """
    Create a minimal git repository for testing.

    Returns a temporary directory initialized as a git repo with
    an initial commit containing a README.
    """
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo, capture_output=True
    )

    # Create initial commit
    readme = repo / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, capture_output=True)

    return repo


# =============================================================================
# Test 1: Snapshot File Tree Integration
# =============================================================================


class TestSnapshotFileTree:
    """Tests for snapshot_file_tree() molecule."""

    def test_captures_git_state(self, git_repo: Path):
        """
        Verify snapshot_file_tree returns dict with git state info.
        """
        # Add some files to the repo
        (git_repo / "src").mkdir()
        (git_repo / "src" / "main.py").write_text("print('hello')")

        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add source files"], cwd=git_repo, capture_output=True)

        snapshot = snapshot_file_tree(git_repo)

        # Verify snapshot contains required fields
        assert isinstance(snapshot, dict)
        assert "head_commit" in snapshot
        assert "git_status" in snapshot
        assert "modified_files" in snapshot

        # head_commit should be a 40-character SHA
        assert len(snapshot["head_commit"]) == 40

    def test_captures_modified_files(self, git_repo: Path):
        """
        Verify snapshot captures files with uncommitted changes.
        """
        # Modify an existing file
        readme = git_repo / "README.md"
        readme.write_text("# Modified Test Repository\n")

        snapshot = snapshot_file_tree(git_repo)

        # README.md should appear in modified_files
        assert "README.md" in snapshot["modified_files"]

    def test_raises_for_nonexistent_directory(self):
        """
        Verify snapshot raises GitSnapshotError for non-existent path.
        """
        with pytest.raises(GitSnapshotError):
            snapshot_file_tree(Path("/nonexistent/directory/path"))


# =============================================================================
# Test 2: Priority-Based Sorting for Conflict Resolution
# =============================================================================


class TestPrioritySorting:
    """Tests for sort_by_priority() atom used in conflict handling."""

    def test_sorts_issues_by_priority(self):
        """
        Verify issues are sorted with highest priority (lowest number) first.
        """
        issues = [
            {"id": "bd-1", "priority": 2},
            {"id": "bd-2", "priority": 0},  # P0 = highest
            {"id": "bd-3", "priority": 1},
        ]

        sorted_issues = sort_by_priority(issues)

        assert sorted_issues[0]["id"] == "bd-2"  # P0 first
        assert sorted_issues[1]["id"] == "bd-3"  # P1 second
        assert sorted_issues[2]["id"] == "bd-1"  # P2 third

    def test_handles_missing_priority(self):
        """
        Verify issues without priority are sorted last.
        """
        issues = [
            {"id": "bd-1"},  # No priority
            {"id": "bd-2", "priority": 0},
        ]

        sorted_issues = sort_by_priority(issues)

        # bd-2 has priority 0, should come first
        assert sorted_issues[0]["id"] == "bd-2"
        assert sorted_issues[1]["id"] == "bd-1"

    def test_preserves_issue_data(self):
        """
        Verify sorting doesn't modify issue data.
        """
        issues = [
            {"id": "bd-1", "priority": 1, "title": "Issue One", "assignee": "atom-writer"},
            {"id": "bd-2", "priority": 0, "title": "Issue Two", "assignee": "molecule-composer"},
        ]

        sorted_issues = sort_by_priority(issues)

        # All fields should be preserved
        assert sorted_issues[0]["title"] == "Issue Two"
        assert sorted_issues[0]["assignee"] == "molecule-composer"
        assert sorted_issues[1]["title"] == "Issue One"


# =============================================================================
# Test 3: Parallelism Recommendations
# =============================================================================


class TestParallelismRecommendations:
    """Tests for recommend_parallelism() atom."""

    def test_scales_up_on_high_success_rate(self):
        """
        Verify parallelism increases when success rate >= 90%.
        """
        # 95% success rate should scale up
        recommended = recommend_parallelism(0.95, current_parallel=2)
        assert recommended == 3

    def test_scales_down_on_low_success_rate(self):
        """
        Verify parallelism decreases when success rate < 70%.
        """
        # 60% success rate should scale down
        recommended = recommend_parallelism(0.60, current_parallel=3)
        assert recommended == 2

    def test_maintains_on_medium_success_rate(self):
        """
        Verify parallelism stays same when success rate is 70-90%.
        """
        # 80% success rate should maintain
        recommended = recommend_parallelism(0.80, current_parallel=2)
        assert recommended == 2

    def test_respects_bounds(self):
        """
        Verify recommendations stay within 1-4 range.
        """
        # Can't scale above 4
        recommended = recommend_parallelism(0.95, current_parallel=4)
        assert recommended == 4

        # Can't scale below 1
        recommended = recommend_parallelism(0.50, current_parallel=1)
        assert recommended == 1


# =============================================================================
# Test 4: Execution Record Creation
# =============================================================================


class TestExecutionRecords:
    """Tests for create_execution_record() atom."""

    def test_creates_valid_record(self):
        """
        Verify execution record contains required fields.
        """
        record = create_execution_record(
            parallel_count=3,
            conflicts=1,
            success=True,
            timestamp="2025-01-15T10:30:00"
        )

        assert record["parallel_count"] == 3
        assert record["conflicts"] == 1
        assert record["success"] is True
        assert record["timestamp"] == "2025-01-15T10:30:00"

    def test_auto_generates_timestamp(self):
        """
        Verify timestamp is auto-generated when not provided.
        """
        record = create_execution_record(
            parallel_count=2,
            conflicts=0,
            success=True
        )

        assert "timestamp" in record
        assert len(record["timestamp"]) > 0

    def test_record_is_json_serializable(self):
        """
        Verify record can be serialized to JSON.
        """
        record = create_execution_record(
            parallel_count=2,
            conflicts=0,
            success=True
        )

        # Should not raise
        json_str = json.dumps(record)
        assert isinstance(json_str, str)


# =============================================================================
# Test 5: Success Rate Calculation
# =============================================================================


class TestSuccessRateCalculation:
    """Tests for calculate_success_rate() atom."""

    def test_calculates_rate_correctly(self):
        """
        Verify success rate is calculated as ratio of successes.
        """
        executions = [
            {"success": True},
            {"success": True},
            {"success": False},
        ]

        rate = calculate_success_rate(executions)

        # 2/3 = 0.666...
        assert 0.66 < rate < 0.67

    def test_returns_zero_for_empty_list(self):
        """
        Verify returns 0.0 for empty execution list.
        """
        rate = calculate_success_rate([])
        assert rate == 0.0

    def test_respects_window_parameter(self):
        """
        Verify only last N executions are considered.
        """
        executions = [
            {"success": False},
            {"success": False},
            {"success": False},
            {"success": True},  # Only these last 2 should be considered
            {"success": True},
        ]

        rate = calculate_success_rate(executions, window=2)

        # Last 2 are both True, so rate should be 1.0
        assert rate == 1.0


# =============================================================================
# Test 6: Error Handling Cascade
# =============================================================================


class TestErrorHandlingCascade:
    """Tests for error handling across orchestration layers."""

    def test_snapshot_handles_non_git_directory(self, tmp_path: Path):
        """
        Verify snapshot_file_tree raises clear error for non-git directory.
        """
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        with pytest.raises(GitSnapshotError) as exc_info:
            snapshot_file_tree(non_git_dir)

        # Error message should be informative
        assert "git" in str(exc_info.value).lower()

    def test_priority_sort_handles_empty_list(self):
        """
        Verify sort_by_priority handles empty list gracefully.
        """
        result = sort_by_priority([])
        assert result == []

    def test_success_rate_handles_no_success_key(self):
        """
        Verify calculate_success_rate handles missing 'success' key.
        """
        executions = [
            {"parallel_count": 2},  # No 'success' key
            {"parallel_count": 2},
        ]

        # Should treat missing 'success' as False
        rate = calculate_success_rate(executions)
        assert rate == 0.0


# =============================================================================
# Test 7: Issue Status Verification Helper
# =============================================================================


class TestIssueStatusVerificationHelper:
    """Tests for the IssueStatusVerificationHelper itself."""

    def test_tracks_status_transitions(self, issue_helper: IssueStatusVerificationHelper):
        """Verify helper correctly tracks status changes."""
        issue_helper.record_status("bd-1", "todo")
        issue_helper.record_status("bd-1", "in_progress")
        issue_helper.record_status("bd-1", "done")

        assert issue_helper.get_status("bd-1") == "done"
        assert issue_helper.get_status_history("bd-1") == ["todo", "in_progress", "done"]

    def test_verifies_specific_transition(self, issue_helper: IssueStatusVerificationHelper):
        """Verify helper can detect specific transitions."""
        issue_helper.record_status("bd-1", "in_progress")
        issue_helper.record_status("bd-1", "done")

        assert issue_helper.verify_transition("bd-1", "in_progress", "done")
        assert not issue_helper.verify_transition("bd-1", "todo", "in_progress")

    def test_detects_rollback_from_comment(self, issue_helper: IssueStatusVerificationHelper):
        """Verify helper detects rollback from comment content."""
        issue_helper.record_status("bd-1", "done")
        issue_helper.record_comment("bd-1", "Rolled back due to conflict with bd-2")

        assert issue_helper.verify_was_rolled_back("bd-1")

    def test_returns_none_for_unknown_issue(self, issue_helper: IssueStatusVerificationHelper):
        """Verify returns None for issues not tracked."""
        assert issue_helper.get_status("unknown-issue") is None
        assert issue_helper.get_status_history("unknown-issue") == []
