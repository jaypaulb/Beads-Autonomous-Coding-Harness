"""
Test Molecules: Conflict Handler
================================

Tests for git merge conflict handling molecules.
Molecules compose atoms into cohesive units for merge operations.
Minimal mocking - only mock subprocess.run for git command execution.
"""

import subprocess
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch, MagicMock

import pytest

# Import molecules (to be implemented)
from src.director.conflict_handler import (
    attempt_automatic_merge,
    detect_merge_conflicts,
    MergeResult,
    MergeStatus,
)


class TestAttemptAutomaticMerge:
    """Tests for attempt_automatic_merge() molecule."""

    def test_returns_merged_on_successful_merge(self, tmp_path):
        """attempt_automatic_merge() returns MergeStatus.MERGED on clean merge."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate successful git merge
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "feature-branch"],
                returncode=0,
                stdout="Merge made by the 'ort' strategy.\n",
                stderr="",
            )

            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            assert result.status == MergeStatus.MERGED
            assert result.error_message is None
            mock_run.assert_called_once()

    def test_returns_conflict_when_merge_has_conflicts(self, tmp_path):
        """attempt_automatic_merge() returns MergeStatus.CONFLICT when conflicts detected."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate merge conflict
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "feature-branch"],
                returncode=1,
                stdout="",
                stderr="CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed; fix conflicts and then commit the result.\n",
            )

            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            assert result.status == MergeStatus.CONFLICT
            assert "CONFLICT" in result.error_message or "conflict" in result.error_message.lower()

    def test_returns_error_on_git_failure(self, tmp_path):
        """attempt_automatic_merge() returns MergeStatus.ERROR on non-conflict git failure."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate git error (e.g., branch doesn't exist)
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "nonexistent-branch"],
                returncode=128,
                stdout="",
                stderr="merge: nonexistent-branch - not something we can merge\n",
            )

            result = attempt_automatic_merge(
                branch_name="nonexistent-branch",
                project_dir=project_dir,
            )

            assert result.status == MergeStatus.ERROR
            assert result.error_message is not None
            assert len(result.error_message) > 0

    def test_returns_error_on_subprocess_exception(self, tmp_path):
        """attempt_automatic_merge() returns MergeStatus.ERROR on subprocess exception."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate subprocess error
            mock_run.side_effect = subprocess.SubprocessError("Git command failed unexpectedly")

            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            # Should return ERROR status, not raise exception
            assert result.status == MergeStatus.ERROR
            assert result.error_message is not None

    def test_handles_already_merged_branch(self, tmp_path):
        """attempt_automatic_merge() handles already-merged branch gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate merge of already-merged branch
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "already-merged-branch"],
                returncode=0,
                stdout="Already up to date.\n",
                stderr="",
            )

            result = attempt_automatic_merge(
                branch_name="already-merged-branch",
                project_dir=project_dir,
            )

            # Should succeed (returncode 0)
            assert result.status == MergeStatus.MERGED
            assert result.error_message is None


class TestDetectMergeConflicts:
    """Tests for detect_merge_conflicts() molecule."""

    def test_returns_empty_list_when_no_conflicts(self, tmp_path):
        """detect_merge_conflicts() returns empty list when working tree is clean."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate clean working tree (no unmerged files)
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "diff", "--name-only", "--diff-filter=U"],
                returncode=0,
                stdout="",
                stderr="",
            )

            conflicts = detect_merge_conflicts(project_dir)

            assert conflicts == []
            mock_run.assert_called_once()

    def test_returns_list_of_conflicted_files(self, tmp_path):
        """detect_merge_conflicts() returns list of files with merge conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate unmerged files
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "diff", "--name-only", "--diff-filter=U"],
                returncode=0,
                stdout="src/main.py\nconfig/settings.json\ntests/test_foo.py\n",
                stderr="",
            )

            conflicts = detect_merge_conflicts(project_dir)

            assert len(conflicts) == 3
            assert "src/main.py" in conflicts
            assert "config/settings.json" in conflicts
            assert "tests/test_foo.py" in conflicts

    def test_handles_subprocess_exception_gracefully(self, tmp_path):
        """detect_merge_conflicts() handles subprocess errors without crashing."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate subprocess error (e.g., not a git repo)
            mock_run.side_effect = subprocess.SubprocessError("fatal: not a git repository")

            # Should not raise, should return empty list or handle gracefully
            conflicts = detect_merge_conflicts(project_dir)

            # Implementation choice: return empty list on error
            assert conflicts == []

    def test_returns_empty_list_for_no_git_repo(self, tmp_path):
        """detect_merge_conflicts() returns empty list when not in a git repo."""
        project_dir = tmp_path / "not_a_repo"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate "not a git repository" error
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "diff", "--name-only", "--diff-filter=U"],
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository (or any of the parent directories): .git\n",
            )

            conflicts = detect_merge_conflicts(project_dir)

            # Should return empty list, not crash
            assert conflicts == []

    def test_handles_whitespace_in_file_names(self, tmp_path):
        """detect_merge_conflicts() handles files with whitespace correctly."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Files with leading/trailing whitespace in output
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "diff", "--name-only", "--diff-filter=U"],
                returncode=0,
                stdout="  src/main.py  \nconfig/settings.json\n\n",
                stderr="",
            )

            conflicts = detect_merge_conflicts(project_dir)

            # Should trim whitespace and skip empty lines
            assert "src/main.py" in conflicts
            assert "config/settings.json" in conflicts
            # Should not include empty strings
            assert "" not in conflicts


class TestFallbackBehavior:
    """Tests verifying that fallback behavior returns usable objects."""

    def test_merge_fallback_returns_error_status_not_exception(self, tmp_path):
        """attempt_automatic_merge() returns ERROR status on failure, not exception."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate complete subprocess failure
            mock_run.side_effect = subprocess.SubprocessError("Git not available")

            # Act: Should not raise exception
            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            # Assert: Returns MergeResult with ERROR status
            assert result is not None
            assert isinstance(result, MergeResult)
            assert result.status == MergeStatus.ERROR
            assert result.error_message is not None

    def test_detect_conflicts_fallback_returns_empty_list_not_exception(self, tmp_path):
        """detect_merge_conflicts() returns empty list on failure, not exception."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate subprocess error
            mock_run.side_effect = subprocess.SubprocessError("Git not available")

            # Act: Should not raise exception
            conflicts = detect_merge_conflicts(project_dir)

            # Assert: Returns empty list
            assert conflicts is not None
            assert isinstance(conflicts, list)
            assert conflicts == []

    def test_merge_result_always_has_valid_status_on_subprocess_error(self, tmp_path):
        """MergeResult always has a valid status enum value on subprocess errors."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # Use SubprocessError which is the type the implementation handles
            mock_run.side_effect = subprocess.SubprocessError("Subprocess failed")

            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            # Status should always be a valid MergeStatus value
            assert result.status in [MergeStatus.MERGED, MergeStatus.CONFLICT, MergeStatus.ERROR]

    def test_merge_result_can_be_used_in_conditional(self, tmp_path):
        """MergeResult can be used in conditional flow without error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("Git unavailable")

            result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            # Can safely use in conditional
            if result.status == MergeStatus.MERGED:
                pass  # Success path
            elif result.status == MergeStatus.CONFLICT:
                # Conflict path - conflicted_files should be accessible
                _ = result.conflicted_files
            else:
                # Error path - error_message should be accessible
                assert result.status == MergeStatus.ERROR
                assert result.error_message is not None
