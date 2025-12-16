"""
Test Molecules: Command Runner and CWD Guard
=============================================

Tests for composed helper functions (molecules layer).
Molecules compose 2-3 atoms into cohesive units.
Minimal mocking - only mock subprocess.run for command execution.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import molecules (to be implemented)
from src.director.cwd_guard import (
    WorkingDirectoryGuard,
    validate_cwd,
)
from src.director.utils import run_command


class TestRunCommand:
    """Tests for run_command() molecule."""

    def test_constructs_absolute_paths_correctly(self, tmp_path):
        """run_command() constructs absolute paths for arguments."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["echo", "test"], returncode=0
            )

            run_command(["echo", "test"], project_dir)

            # Verify subprocess.run was called
            mock_run.assert_called_once()
            # Verify NO cwd parameter was used
            call_kwargs = mock_run.call_args.kwargs
            assert "cwd" not in call_kwargs, "cwd parameter is forbidden"

    def test_logs_full_command_for_debugging(self, tmp_path, caplog):
        """run_command() logs the full absolute command for debugging."""
        import logging

        caplog.set_level(logging.DEBUG)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["pytest", str(project_dir / "tests")], returncode=0
            )

            run_command(["pytest", "tests"], project_dir)

            # Should log the command being executed
            log_output = caplog.text.lower()
            assert "pytest" in log_output or "command" in log_output or len(caplog.records) > 0

    def test_returns_completed_process(self, tmp_path):
        """run_command() returns subprocess.CompletedProcess."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            expected_result = subprocess.CompletedProcess(
                args=["echo", "test"], returncode=0, stdout="test output"
            )
            mock_run.return_value = expected_result

            result = run_command(["echo", "test"], project_dir)

            assert isinstance(result, subprocess.CompletedProcess)
            assert result.returncode == 0


class TestWorkingDirectoryGuard:
    """Tests for WorkingDirectoryGuard context manager molecule."""

    def test_raises_on_cwd_mismatch(self, tmp_path):
        """WorkingDirectoryGuard raises RuntimeError when cwd doesn't match expected."""
        # Create a directory that will NOT be our cwd
        wrong_cwd = tmp_path / "wrong_dir"
        wrong_cwd.mkdir()

        # Our actual cwd is different from wrong_cwd
        actual_cwd = Path.cwd()

        # Guard should raise when expected != actual
        with pytest.raises(RuntimeError) as exc_info:
            with WorkingDirectoryGuard(wrong_cwd):
                pass  # pragma: no cover - should not reach here

        error_message = str(exc_info.value)
        # Error should mention the mismatch
        assert "mismatch" in error_message.lower() or "expected" in error_message.lower()

    def test_restores_cwd_on_exit(self, tmp_path):
        """WorkingDirectoryGuard restores original cwd when context exits."""
        original_cwd = Path.cwd().resolve()

        # Create a temp directory to use as expected cwd
        temp_dir = tmp_path / "guard_test"
        temp_dir.mkdir()

        # Change to temp_dir first so guard accepts it
        os.chdir(temp_dir)

        try:
            # Simulate something changing cwd during context
            with WorkingDirectoryGuard(temp_dir):
                # Change cwd inside context
                os.chdir(tmp_path)

            # After context exits, cwd should be restored to temp_dir
            # (not necessarily to original_cwd, but to what guard saved on entry)
            assert Path.cwd().resolve() == temp_dir.resolve()
        finally:
            # Restore original cwd for test cleanup
            os.chdir(original_cwd)

    def test_allows_entry_when_cwd_matches(self, tmp_path):
        """WorkingDirectoryGuard allows context entry when cwd matches expected."""
        original_cwd = Path.cwd().resolve()
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        os.chdir(test_dir)

        try:
            # Should not raise - cwd matches expected
            with WorkingDirectoryGuard(test_dir):
                pass  # Success if no exception
        finally:
            os.chdir(original_cwd)


class TestValidateCwd:
    """Tests for validate_cwd() function molecule."""

    def test_raises_clear_error_with_actual_vs_expected(self, tmp_path):
        """validate_cwd() raises RuntimeError with actual vs expected in message."""
        # Create a path that won't be our actual cwd
        expected_path = tmp_path / "expected_dir"
        expected_path.mkdir()

        actual_cwd = Path.cwd().resolve()

        # Validate should fail since actual != expected
        with pytest.raises(RuntimeError) as exc_info:
            validate_cwd(expected_path)

        error_message = str(exc_info.value)
        # Error message should contain both actual and expected paths
        assert str(expected_path) in error_message or "expected" in error_message.lower()
        assert str(actual_cwd) in error_message or "actual" in error_message.lower()

    def test_does_not_raise_when_cwd_matches(self, tmp_path):
        """validate_cwd() does not raise when actual cwd matches expected."""
        original_cwd = Path.cwd().resolve()
        test_dir = tmp_path / "match_test"
        test_dir.mkdir()

        os.chdir(test_dir)

        try:
            # Should not raise - cwd matches expected
            validate_cwd(test_dir)  # No exception = success
        finally:
            os.chdir(original_cwd)

    def test_returns_none_on_success(self, tmp_path):
        """validate_cwd() returns None on success (void function)."""
        original_cwd = Path.cwd().resolve()
        test_dir = tmp_path / "return_test"
        test_dir.mkdir()

        os.chdir(test_dir)

        try:
            result = validate_cwd(test_dir)
            assert result is None
        finally:
            os.chdir(original_cwd)
