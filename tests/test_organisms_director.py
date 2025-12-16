"""
Organism Tests: Director Module Integration
============================================

Organism-level integration tests for the Director module.
Tests how molecules work together as cohesive feature units:
- Timeout handling with cleanup callbacks
- BV plan query integrated with timeout
- Conflict detection integrated with merge attempts
- Graceful fallback when components unavailable

These tests verify the composition of molecules, NOT individual atoms.
External dependencies (subprocess, filesystem) are mocked where necessary.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Import organisms and molecules under test
from src.director.timeout_organisms import (
    run_with_timeout,
    run_with_timeout_and_cancel,
    TimeoutError,
    TimeoutResult,
)
from src.director.bv_robot_plan import (
    BVRobotPlan,
    query_bv_robot_plan,
    parse_bv_plan_output,
)
from src.director.conflict_handler import (
    MergeStatus,
    MergeResult,
    attempt_automatic_merge,
    detect_merge_conflicts,
)
from src.director.cwd_guard import (
    WorkingDirectoryGuard,
    validate_cwd,
)


# =============================================================================
# Organism Test: Timeout + Cleanup Callback Integration
# =============================================================================


class TestTimeoutWithCleanupIntegration:
    """
    Organism tests for timeout handling with cleanup callbacks.

    Verifies that cleanup callbacks integrate correctly with timeout:
    - Cleanup is called when timeout occurs
    - Cleanup has its own grace period
    - Cleanup failures don't hide timeout status
    """

    @pytest.mark.asyncio
    async def test_timeout_triggers_cleanup_callback_before_returning(self):
        """
        Organism: Timeout triggers cleanup before returning result.

        Flow:
        1. Start slow operation with cleanup callback
        2. Operation times out
        3. Cleanup callback is invoked
        4. TimeoutResult is returned after cleanup completes
        """
        # Arrange
        cleanup_sequence = []

        async def slow_operation():
            cleanup_sequence.append("operation_started")
            await asyncio.sleep(10)  # Will timeout
            cleanup_sequence.append("operation_completed")  # Never reached

        async def cleanup_callback():
            cleanup_sequence.append("cleanup_called")

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            operation_name="slow_with_cleanup",
            cleanup_callback=cleanup_callback,
            raise_on_timeout=False,
        )

        # Assert
        assert result.timed_out is True
        assert "operation_started" in cleanup_sequence
        assert "cleanup_called" in cleanup_sequence
        assert "operation_completed" not in cleanup_sequence
        # Cleanup should be called after operation starts but before return
        assert cleanup_sequence.index("cleanup_called") > cleanup_sequence.index("operation_started")

    @pytest.mark.asyncio
    async def test_cleanup_failure_preserves_timeout_status(self):
        """
        Organism: Cleanup failure doesn't change timeout status.

        Even if cleanup callback raises, the TimeoutResult should still
        indicate timed_out=True and the original timeout information.
        """
        # Arrange
        async def slow_operation():
            await asyncio.sleep(10)

        async def failing_cleanup():
            raise RuntimeError("Cleanup exploded")

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            operation_name="slow_with_failing_cleanup",
            cleanup_callback=failing_cleanup,
            raise_on_timeout=False,
        )

        # Assert
        assert result.timed_out is True
        assert result.success is False
        assert isinstance(result.error, TimeoutError)
        assert result.error.operation_name == "slow_with_failing_cleanup"

    @pytest.mark.asyncio
    async def test_slow_cleanup_gets_grace_period(self):
        """
        Organism: Slow cleanup callback gets grace period before being cut off.

        The cleanup callback should have CLEANUP_GRACE_PERIOD_SECONDS to complete.
        """
        # Arrange
        cleanup_stages = []

        async def slow_operation():
            await asyncio.sleep(10)

        async def slow_cleanup():
            cleanup_stages.append("cleanup_start")
            await asyncio.sleep(0.05)  # Short delay (less than grace period)
            cleanup_stages.append("cleanup_finish")

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            operation_name="slow_op",
            cleanup_callback=slow_cleanup,
            raise_on_timeout=False,
        )

        # Assert
        assert result.timed_out is True
        assert "cleanup_start" in cleanup_stages
        assert "cleanup_finish" in cleanup_stages  # Cleanup completed within grace period


# =============================================================================
# Organism Test: BV Plan Query + Timeout Integration
# =============================================================================


class TestBVPlanQueryWithTimeout:
    """
    Organism tests for BV robot plan query with timeout behavior.

    The query_bv_robot_plan molecule has its own timeout, but we test
    how it integrates into a larger timeout-wrapped workflow.
    """

    def test_bv_query_respects_internal_timeout(self):
        """
        Organism: BV query times out when subprocess hangs.

        The query_bv_robot_plan has a timeout_seconds parameter
        that should terminate hung subprocess calls.
        """
        # Arrange: Mock subprocess.run to hang (via TimeoutExpired)
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which", return_value="/usr/bin/bv"):
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["bv", "robot", "--plan"],
                timeout=1,
            )

            # Act
            result = query_bv_robot_plan(timeout_seconds=1)

            # Assert
            assert result.success is False
            # Error message says "timed out" not "timeout"
            assert "timed out" in result.error_message.lower()

    def test_bv_query_graceful_fallback_on_unavailable(self):
        """
        Organism: BV query returns empty plan when CLI unavailable.

        When BV is not installed, the query should return a valid
        BVRobotPlan with success=False and helpful error message.
        """
        # Arrange: Mock shutil.which to return None (not found)
        with patch("shutil.which", return_value=None):
            # Act
            result = query_bv_robot_plan()

            # Assert
            assert result.success is False
            assert result.error_message is not None
            assert "unavailable" in result.error_message.lower() or "not found" in result.error_message.lower()
            assert result.phases == []
            assert result.raw_output == ""


# =============================================================================
# Organism Test: Conflict Handler + Detection Integration
# =============================================================================


class TestConflictHandlerIntegration:
    """
    Organism tests for conflict handler molecules working together.

    Tests the flow: attempt_merge -> detect if conflict -> return details.
    """

    def test_merge_with_conflict_returns_conflicted_files(self, tmp_path):
        """
        Organism: Merge conflict returns list of conflicted files.

        Flow:
        1. attempt_automatic_merge encounters conflict
        2. detect_merge_conflicts is called
        3. Result includes both status and file list
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Arrange: First call is merge (conflict), second is detect conflicts
        call_count = [0]

        def mock_subprocess_run(*args, **kwargs):
            call_count[0] += 1
            cmd = args[0]

            if "merge" in cmd:
                # First call: git merge fails with conflict
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=1,
                    stdout="",
                    stderr="CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed",
                )
            elif "diff" in cmd:
                # Second call: git diff --diff-filter=U shows conflicts
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout="src/main.py\nconfig.json\n",
                    stderr="",
                )
            else:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            # Act
            result = attempt_automatic_merge(
                branch_name="feature-with-conflicts",
                project_dir=project_dir,
            )

            # Assert
            assert result.status == MergeStatus.CONFLICT
            assert result.conflicted_files is not None
            assert len(result.conflicted_files) == 2
            assert "src/main.py" in result.conflicted_files
            assert "config.json" in result.conflicted_files

    def test_successful_merge_returns_no_conflict_files(self, tmp_path):
        """
        Organism: Clean merge returns no conflicted files.

        When merge succeeds, conflicted_files should be None or empty.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "feature"],
                returncode=0,
                stdout="Merge made by the 'ort' strategy.",
                stderr="",
            )

            # Act
            result = attempt_automatic_merge(
                branch_name="feature",
                project_dir=project_dir,
            )

            # Assert
            assert result.status == MergeStatus.MERGED
            assert result.conflicted_files is None
            assert result.error_message is None


# =============================================================================
# Organism Test: CWD Guard + Operation Integration
# =============================================================================


class TestCWDGuardOperationIntegration:
    """
    Organism tests for CWD guard protecting operations.

    Verifies that WorkingDirectoryGuard integrates with operations
    to maintain cwd consistency.
    """

    def test_guard_protects_operation_that_changes_cwd(self, tmp_path):
        """
        Organism: Guard restores cwd after operation changes it.

        Flow:
        1. Enter guard with expected cwd
        2. Operation changes cwd to different directory
        3. Guard restores original cwd on exit
        """
        import os

        original_cwd = Path.cwd().resolve()
        expected_dir = tmp_path / "expected"
        other_dir = tmp_path / "other"
        expected_dir.mkdir()
        other_dir.mkdir()

        os.chdir(expected_dir)

        try:
            with WorkingDirectoryGuard(expected_dir):
                # Simulate operation that changes cwd
                os.chdir(other_dir)
                assert Path.cwd().resolve() == other_dir.resolve()

            # After guard exit, cwd should be restored
            assert Path.cwd().resolve() == expected_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_guard_fails_fast_on_wrong_cwd(self, tmp_path):
        """
        Organism: Guard raises immediately if cwd doesn't match expected.

        The guard should fail on __enter__ if cwd is wrong,
        preventing any operations from running with wrong state.
        """
        import os

        original_cwd = Path.cwd().resolve()
        expected_dir = tmp_path / "expected"
        wrong_dir = tmp_path / "wrong"
        expected_dir.mkdir()
        wrong_dir.mkdir()

        os.chdir(wrong_dir)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                with WorkingDirectoryGuard(expected_dir):
                    pytest.fail("Should not reach here - guard should fail on entry")

            assert "mismatch" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Organism Test: Graceful Degradation
# =============================================================================


class TestGracefulDegradation:
    """
    Organism tests for graceful degradation when components fail.

    The Director module should handle failures gracefully:
    - Missing BV CLI -> empty plan
    - Git errors -> error status (not crash)
    - Timeout -> cleanup + status (not hang)
    """

    def test_bv_plan_failure_returns_usable_empty_plan(self):
        """
        Organism: BV failure returns valid empty BVRobotPlan.

        The returned plan should be usable (not None, not raise)
        even when BV is unavailable or fails.
        """
        with patch("shutil.which", return_value=None):
            plan = query_bv_robot_plan()

            # Should be able to use the plan object without checking success first
            assert isinstance(plan, BVRobotPlan)
            assert plan.phases == []  # Empty but valid
            assert plan.raw_output == ""  # Empty but valid

            # Can iterate over phases without error
            for phase in plan.phases:
                pass  # No error

    def test_conflict_handler_subprocess_error_returns_status(self, tmp_path):
        """
        Organism: Subprocess error returns ERROR status, not exception.

        When subprocess.run raises SubprocessError, the conflict handler
        should catch it and return MergeResult with ERROR status.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.SubprocessError("Process died")

            result = attempt_automatic_merge(
                branch_name="some-branch",
                project_dir=project_dir,
            )

            # Should return error status, not raise
            assert result.status == MergeStatus.ERROR
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_timeout_organism_handles_cancelled_task(self):
        """
        Organism: Cancelled task is handled gracefully.

        If a task is externally cancelled, the timeout organism
        should return a result (not propagate CancelledError).
        """
        async def slow_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(slow_task())

        # Start monitoring the task
        monitor_task = asyncio.create_task(
            run_with_timeout_and_cancel(task, timeout_seconds=5.0)
        )

        # Give it a moment to start
        await asyncio.sleep(0.05)

        # Externally cancel the task
        task.cancel()

        # Monitor should return result, not raise
        result = await monitor_task

        assert result.success is False
        # Either timed_out=False + cancelled error, or task completed before check
        assert result.error is not None or result.timed_out is False
