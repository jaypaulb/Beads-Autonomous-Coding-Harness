"""
Integration Tests: Director Flow End-to-End
============================================

End-to-end integration tests for the Director module workflow.
Tests the full flow of components working together:
- Query BV plan -> get task list
- Spawn sub-agent -> execute with timeout
- Handle timeout -> cleanup and report
- Check conflicts -> detect and report

These tests simulate realistic usage scenarios with mocked external
dependencies (subprocess, filesystem) to verify the integration.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Import all components being integrated
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
from src.director.utils import (
    resolve_absolute_path,
    validate_path_is_absolute,
)


# =============================================================================
# E2E Flow Test: Query Plan -> Execute -> Handle Result
# =============================================================================


class TestDirectorWorkflowE2E:
    """
    End-to-end tests for the Director workflow.

    Simulates the full flow a Director would execute:
    1. Query BV for execution plan
    2. For each task in plan, spawn sub-agent with timeout
    3. Handle timeouts with cleanup
    4. After agent completes, check for conflicts
    """

    @pytest.mark.asyncio
    async def test_full_workflow_successful_execution(self, tmp_path):
        """
        E2E: Full Director workflow executes successfully.

        Flow:
        1. Query BV plan (mocked to return 2 phases)
        2. Execute first "task" (async operation) with timeout
        3. Task completes within timeout
        4. Check for conflicts (none found)
        5. Return success
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock BV plan query
        mock_plan_output = """ROBOT EXECUTION PLAN
===================

Phase 1: Setup
--------------
- Task A

Phase 2: Implementation
-----------------------
- Task B
"""
        with patch("shutil.which", return_value="/usr/bin/bv"), \
             patch("subprocess.run") as mock_run:

            # Mock BV CLI response
            mock_run.return_value = subprocess.CompletedProcess(
                args=["bv", "robot", "--plan"],
                returncode=0,
                stdout=mock_plan_output,
                stderr="",
            )

            # Step 1: Query BV plan
            plan = query_bv_robot_plan()
            assert plan.success is True
            assert len(plan.phases) == 2

            # Step 2: Execute a task with timeout
            async def execute_task():
                await asyncio.sleep(0.05)  # Quick task
                return {"status": "completed", "artifacts": ["file.py"]}

            result = await run_with_timeout(
                execute_task(),
                timeout_seconds=1.0,
                operation_name="task_a",
                raise_on_timeout=False,
            )

            assert result.success is True
            assert result.result["status"] == "completed"

            # Step 3: Check for conflicts (reset mock for git command)
            mock_run.reset_mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "diff", "--name-only", "--diff-filter=U"],
                returncode=0,
                stdout="",  # No conflicts
                stderr="",
            )

            conflicts = detect_merge_conflicts(project_dir)
            assert conflicts == []

    @pytest.mark.asyncio
    async def test_workflow_handles_timeout_with_cleanup(self, tmp_path):
        """
        E2E: Workflow handles task timeout with cleanup callback.

        Flow:
        1. Start task that will timeout
        2. Timeout triggers cleanup callback
        3. Cleanup records what was running
        4. Result indicates timeout and cleanup ran
        """
        # Track cleanup execution
        cleanup_context = {"ran": False, "operation": None}

        async def slow_task():
            await asyncio.sleep(10)  # Will timeout
            return {"status": "should_not_reach"}

        async def cleanup_on_timeout():
            cleanup_context["ran"] = True
            cleanup_context["operation"] = "slow_task"

        # Execute with short timeout
        result = await run_with_timeout(
            slow_task(),
            timeout_seconds=0.1,
            operation_name="slow_task",
            cleanup_callback=cleanup_on_timeout,
            raise_on_timeout=False,
        )

        # Verify timeout handling
        assert result.success is False
        assert result.timed_out is True
        assert cleanup_context["ran"] is True
        assert cleanup_context["operation"] == "slow_task"

    @pytest.mark.asyncio
    async def test_workflow_detects_conflicts_after_merge(self, tmp_path):
        """
        E2E: Workflow detects conflicts after merge attempt.

        Flow:
        1. Attempt merge (conflicts occur)
        2. Detect conflicted files
        3. Return conflict information for resolution
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # First call: git merge (conflict)
            # Second call: git diff (list conflicts)
            call_count = [0]

            def mock_git_commands(*args, **kwargs):
                call_count[0] += 1
                cmd = args[0]

                if "merge" in cmd:
                    return subprocess.CompletedProcess(
                        args=cmd,
                        returncode=1,
                        stdout="",
                        stderr="CONFLICT (content): Merge conflict in api.py\n",
                    )
                elif "diff" in cmd:
                    return subprocess.CompletedProcess(
                        args=cmd,
                        returncode=0,
                        stdout="src/api.py\nconfig/settings.json\n",
                        stderr="",
                    )
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            mock_run.side_effect = mock_git_commands

            # Step 1: Attempt merge
            merge_result = attempt_automatic_merge(
                branch_name="feature-branch",
                project_dir=project_dir,
            )

            # Step 2: Verify conflict detected
            assert merge_result.status == MergeStatus.CONFLICT
            assert merge_result.conflicted_files is not None
            assert "src/api.py" in merge_result.conflicted_files
            assert "config/settings.json" in merge_result.conflicted_files


# =============================================================================
# E2E Flow Test: Error Propagation
# =============================================================================


class TestErrorPropagationE2E:
    """
    End-to-end tests for error propagation through the stack.

    Verifies that errors at any layer are properly communicated
    up the stack without crashing the workflow.
    """

    def test_bv_unavailable_propagates_gracefully(self):
        """
        E2E: BV unavailability propagates as usable error result.

        When BV CLI is not installed, the workflow should:
        1. Return a BVRobotPlan with success=False
        2. Include helpful error message
        3. Not raise any exceptions
        """
        with patch("shutil.which", return_value=None):
            plan = query_bv_robot_plan()

            # Should get usable result, not exception
            assert isinstance(plan, BVRobotPlan)
            assert plan.success is False
            assert plan.error_message is not None
            # Workflow can check this and decide what to do
            assert len(plan.phases) == 0

    def test_git_error_propagates_as_merge_error(self, tmp_path):
        """
        E2E: Git errors propagate as MergeStatus.ERROR.

        When git fails (e.g., not a repo), the workflow should:
        1. Return MergeResult with ERROR status
        2. Include error message
        3. Not raise exceptions
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "merge", "branch"],
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository",
            )

            result = attempt_automatic_merge(
                branch_name="branch",
                project_dir=project_dir,
            )

            # Error propagates as status, not exception
            assert result.status == MergeStatus.ERROR
            assert "not a git repository" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_async_exception_propagates_in_result(self):
        """
        E2E: Async task exceptions propagate in TimeoutResult.

        When a task raises an exception, the workflow should:
        1. Return TimeoutResult with success=False
        2. Include the original exception in result.error
        3. Not re-raise unless configured to
        """
        async def failing_task():
            raise ValueError("Task failed with specific error")

        result = await run_with_timeout(
            failing_task(),
            timeout_seconds=5.0,
            operation_name="failing_task",
            raise_on_timeout=False,
        )

        # Exception propagates in result
        assert result.success is False
        assert result.timed_out is False
        assert isinstance(result.error, ValueError)
        assert "specific error" in str(result.error)


# =============================================================================
# E2E Flow Test: Cleanup on Failure
# =============================================================================


class TestCleanupOnFailureE2E:
    """
    End-to-end tests for cleanup behavior on various failure modes.
    """

    @pytest.mark.asyncio
    async def test_cleanup_runs_on_timeout(self):
        """
        E2E: Cleanup callback runs when operation times out.
        """
        cleanup_ran = False

        async def slow_operation():
            await asyncio.sleep(10)

        async def cleanup():
            nonlocal cleanup_ran
            cleanup_ran = True

        await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            cleanup_callback=cleanup,
            raise_on_timeout=False,
        )

        assert cleanup_ran is True

    @pytest.mark.asyncio
    async def test_cleanup_does_not_run_on_success(self):
        """
        E2E: Cleanup callback does NOT run on successful completion.
        """
        cleanup_ran = False

        async def quick_operation():
            return "done"

        async def cleanup():
            nonlocal cleanup_ran
            cleanup_ran = True

        result = await run_with_timeout(
            quick_operation(),
            timeout_seconds=5.0,
            cleanup_callback=cleanup,
            raise_on_timeout=False,
        )

        assert result.success is True
        assert cleanup_ran is False

    @pytest.mark.asyncio
    async def test_cleanup_runs_even_when_failing(self):
        """
        E2E: Cleanup runs even if it fails, and timeout is still reported.
        """
        async def slow_operation():
            await asyncio.sleep(10)

        async def failing_cleanup():
            raise RuntimeError("Cleanup crashed")

        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            cleanup_callback=failing_cleanup,
            raise_on_timeout=False,
        )

        # Timeout is still the reported status
        assert result.timed_out is True
        assert result.success is False


# =============================================================================
# E2E Flow Test: Multiple Tasks with Timeout Management
# =============================================================================


class TestMultipleTasksE2E:
    """
    End-to-end tests for managing multiple tasks with timeout.
    """

    @pytest.mark.asyncio
    async def test_parallel_tasks_with_individual_timeouts(self):
        """
        E2E: Multiple tasks can be run with individual timeout management.

        This simulates a Director spawning multiple sub-agents and
        managing their timeouts independently.
        """
        results = []

        async def quick_task(task_id: str):
            await asyncio.sleep(0.05)
            return f"completed_{task_id}"

        async def slow_task(task_id: str):
            await asyncio.sleep(10)
            return f"should_not_complete_{task_id}"

        # Create tasks with different durations
        task1 = asyncio.create_task(quick_task("1"))
        task2 = asyncio.create_task(slow_task("2"))
        task3 = asyncio.create_task(quick_task("3"))

        # Run with timeout management
        result1 = await run_with_timeout_and_cancel(task1, timeout_seconds=1.0, operation_name="task_1")
        result2 = await run_with_timeout_and_cancel(task2, timeout_seconds=0.1, operation_name="task_2")
        result3 = await run_with_timeout_and_cancel(task3, timeout_seconds=1.0, operation_name="task_3")

        # Task 1 and 3 should complete
        assert result1.success is True
        assert result1.result == "completed_1"

        assert result3.success is True
        assert result3.result == "completed_3"

        # Task 2 should timeout
        assert result2.success is False
        assert result2.timed_out is True

    @pytest.mark.asyncio
    async def test_sequential_tasks_share_workflow_state(self):
        """
        E2E: Sequential tasks can share workflow state.

        Simulates a Director workflow where task results feed into
        the next task's input.
        """
        workflow_state = {"phase": 0, "artifacts": []}

        async def phase_1_task():
            workflow_state["phase"] = 1
            workflow_state["artifacts"].append("model.py")
            return {"phase": 1, "output": "model created"}

        async def phase_2_task():
            # Uses output from phase 1
            assert workflow_state["phase"] == 1
            workflow_state["phase"] = 2
            workflow_state["artifacts"].append("api.py")
            return {"phase": 2, "output": "api created", "depends_on": workflow_state["artifacts"]}

        # Execute phase 1
        result1 = await run_with_timeout(
            phase_1_task(),
            timeout_seconds=1.0,
            operation_name="phase_1",
            raise_on_timeout=False,
        )
        assert result1.success is True

        # Execute phase 2 (depends on phase 1 completing)
        result2 = await run_with_timeout(
            phase_2_task(),
            timeout_seconds=1.0,
            operation_name="phase_2",
            raise_on_timeout=False,
        )
        assert result2.success is True
        assert "model.py" in result2.result["depends_on"]

        # Final state
        assert workflow_state["phase"] == 2
        assert len(workflow_state["artifacts"]) == 2
