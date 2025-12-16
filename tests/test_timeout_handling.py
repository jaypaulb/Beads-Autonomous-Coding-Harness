"""
Test Timeout Handling
======================

Tests for async timeout handling atoms and organisms.
Tests cover: normal completion, timeout triggered, cleanup on timeout.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.director.timeout_atoms import (
    DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    VERIFICATION_TIMEOUT_SECONDS,
    CLI_QUERY_TIMEOUT_SECONDS,
    CLEANUP_GRACE_PERIOD_SECONDS,
)
from src.director.timeout_organisms import (
    run_with_timeout,
    run_with_timeout_and_cancel,
    TimeoutError,
    TimeoutResult,
)


# =============================================================================
# Atom Tests - Timeout Constants
# =============================================================================


class TestTimeoutConstants:
    """Tests for timeout constant atoms."""

    def test_default_subagent_timeout_is_600_seconds(self):
        """DEFAULT_SUBAGENT_TIMEOUT_SECONDS should be 600 (10 minutes)."""
        assert DEFAULT_SUBAGENT_TIMEOUT_SECONDS == 600

    def test_verification_timeout_is_30_seconds(self):
        """VERIFICATION_TIMEOUT_SECONDS should be 30."""
        assert VERIFICATION_TIMEOUT_SECONDS == 30

    def test_cli_query_timeout_is_10_seconds(self):
        """CLI_QUERY_TIMEOUT_SECONDS should be 10."""
        assert CLI_QUERY_TIMEOUT_SECONDS == 10

    def test_cleanup_grace_period_is_5_seconds(self):
        """CLEANUP_GRACE_PERIOD_SECONDS should be 5.0."""
        assert CLEANUP_GRACE_PERIOD_SECONDS == 5.0


# =============================================================================
# Organism Tests - run_with_timeout
# =============================================================================


class TestRunWithTimeoutNormalCompletion:
    """Tests for run_with_timeout() when operation completes normally."""

    @pytest.mark.asyncio
    async def test_returns_result_on_normal_completion(self):
        """run_with_timeout() returns the coroutine result when it completes."""
        # Arrange
        async def quick_operation():
            return "success_value"

        # Act
        result = await run_with_timeout(
            quick_operation(),
            timeout_seconds=5.0,
            operation_name="quick_op",
        )

        # Assert
        assert result == "success_value"

    @pytest.mark.asyncio
    async def test_returns_timeout_result_on_normal_completion_no_raise(self):
        """run_with_timeout() returns TimeoutResult with success=True."""
        # Arrange
        async def quick_operation():
            return 42

        # Act
        result = await run_with_timeout(
            quick_operation(),
            timeout_seconds=5.0,
            operation_name="quick_op",
            raise_on_timeout=False,
        )

        # Assert
        assert isinstance(result, TimeoutResult)
        assert result.success is True
        assert result.result == 42
        assert result.timed_out is False
        assert result.error is None
        assert result.elapsed_seconds >= 0

    @pytest.mark.asyncio
    async def test_elapsed_time_is_tracked(self):
        """run_with_timeout() tracks elapsed time correctly."""
        # Arrange
        async def delayed_operation():
            await asyncio.sleep(0.1)
            return "done"

        # Act
        result = await run_with_timeout(
            delayed_operation(),
            timeout_seconds=5.0,
            raise_on_timeout=False,
        )

        # Assert
        assert result.success is True
        assert result.elapsed_seconds >= 0.1
        assert result.elapsed_seconds < 1.0  # Should not be wildly off


class TestRunWithTimeoutTriggered:
    """Tests for run_with_timeout() when timeout is triggered."""

    @pytest.mark.asyncio
    async def test_raises_timeout_error_when_exceeded(self):
        """run_with_timeout() raises TimeoutError when operation times out."""
        # Arrange
        async def slow_operation():
            await asyncio.sleep(10)  # Would take 10 seconds
            return "should_not_reach"

        # Act & Assert
        with pytest.raises(TimeoutError) as exc_info:
            await run_with_timeout(
                slow_operation(),
                timeout_seconds=0.1,  # Very short timeout
                operation_name="slow_op",
            )

        assert exc_info.value.operation_name == "slow_op"
        assert exc_info.value.timeout_seconds == 0.1

    @pytest.mark.asyncio
    async def test_returns_timeout_result_when_not_raising(self):
        """run_with_timeout() returns TimeoutResult with timed_out=True."""
        # Arrange
        async def slow_operation():
            await asyncio.sleep(10)
            return "should_not_reach"

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            operation_name="slow_op",
            raise_on_timeout=False,
        )

        # Assert
        assert isinstance(result, TimeoutResult)
        assert result.success is False
        assert result.timed_out is True
        assert result.result is None
        assert isinstance(result.error, TimeoutError)

    @pytest.mark.asyncio
    async def test_timeout_error_contains_context(self):
        """TimeoutError includes operation name and timeout value."""
        # Arrange
        async def slow_operation():
            await asyncio.sleep(10)

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.05,
            operation_name="named_operation",
            raise_on_timeout=False,
        )

        # Assert
        assert result.error.operation_name == "named_operation"
        assert result.error.timeout_seconds == 0.05
        assert "named_operation" in str(result.error)
        assert "0.05" in str(result.error)


class TestRunWithTimeoutCleanup:
    """Tests for run_with_timeout() cleanup callback behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_callback_called_on_timeout(self):
        """Cleanup callback is invoked when operation times out."""
        # Arrange
        cleanup_called = False

        async def slow_operation():
            await asyncio.sleep(10)

        async def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        # Act
        await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            cleanup_callback=cleanup,
            raise_on_timeout=False,
        )

        # Assert
        assert cleanup_called is True

    @pytest.mark.asyncio
    async def test_cleanup_not_called_on_success(self):
        """Cleanup callback is NOT invoked when operation succeeds."""
        # Arrange
        cleanup_called = False

        async def quick_operation():
            return "done"

        async def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        # Act
        await run_with_timeout(
            quick_operation(),
            timeout_seconds=5.0,
            cleanup_callback=cleanup,
            raise_on_timeout=False,
        )

        # Assert
        assert cleanup_called is False

    @pytest.mark.asyncio
    async def test_cleanup_failure_does_not_suppress_timeout(self):
        """If cleanup fails, the timeout is still reported."""
        # Arrange
        async def slow_operation():
            await asyncio.sleep(10)

        async def failing_cleanup():
            raise ValueError("cleanup failed")

        # Act
        result = await run_with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            cleanup_callback=failing_cleanup,
            raise_on_timeout=False,
        )

        # Assert
        assert result.timed_out is True
        assert result.success is False


# =============================================================================
# Organism Tests - run_with_timeout_and_cancel
# =============================================================================


class TestRunWithTimeoutAndCancel:
    """Tests for run_with_timeout_and_cancel() task management."""

    @pytest.mark.asyncio
    async def test_returns_result_on_normal_completion(self):
        """Task result is returned when it completes within timeout."""
        # Arrange
        async def quick_task():
            return "task_result"

        task = asyncio.create_task(quick_task())

        # Act
        result = await run_with_timeout_and_cancel(
            task,
            timeout_seconds=5.0,
            operation_name="quick_task",
        )

        # Assert
        assert result.success is True
        assert result.result == "task_result"
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_cancels_task_on_timeout(self):
        """Task is cancelled when it exceeds timeout."""
        # Arrange
        task_cancelled = False

        async def slow_task():
            nonlocal task_cancelled
            try:
                await asyncio.sleep(10)
                return "should_not_reach"
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        task = asyncio.create_task(slow_task())

        # Act
        result = await run_with_timeout_and_cancel(
            task,
            timeout_seconds=0.1,
            operation_name="slow_task",
        )

        # Assert
        assert result.success is False
        assert result.timed_out is True
        assert task_cancelled is True
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_handles_task_exception(self):
        """Exceptions from the task are captured in result."""
        # Arrange
        async def failing_task():
            raise ValueError("task_error")

        task = asyncio.create_task(failing_task())

        # Act
        result = await run_with_timeout_and_cancel(
            task,
            timeout_seconds=5.0,
            operation_name="failing_task",
        )

        # Assert
        assert result.success is False
        assert result.timed_out is False
        assert isinstance(result.error, ValueError)
        assert "task_error" in str(result.error)


# =============================================================================
# TimeoutResult Tests
# =============================================================================


class TestTimeoutResult:
    """Tests for TimeoutResult container."""

    def test_repr_shows_success(self):
        """TimeoutResult repr shows success state."""
        result = TimeoutResult(success=True, result=42, elapsed_seconds=1.5)
        repr_str = repr(result)

        assert "success=True" in repr_str
        assert "1.50s" in repr_str

    def test_repr_shows_timeout(self):
        """TimeoutResult repr shows timeout state."""
        result = TimeoutResult(
            success=False,
            timed_out=True,
            elapsed_seconds=5.0,
        )
        repr_str = repr(result)

        assert "timed_out=True" in repr_str
        assert "5.00s" in repr_str

    def test_repr_shows_error(self):
        """TimeoutResult repr shows error state."""
        result = TimeoutResult(
            success=False,
            error=ValueError("test"),
            elapsed_seconds=0.5,
        )
        repr_str = repr(result)

        assert "error=" in repr_str


# =============================================================================
# TimeoutError Tests
# =============================================================================


class TestTimeoutError:
    """Tests for custom TimeoutError exception."""

    def test_error_message_includes_operation_and_timeout(self):
        """TimeoutError message includes operation name and timeout value."""
        error = TimeoutError(
            operation_name="test_operation",
            timeout_seconds=60.0,
        )

        assert "test_operation" in str(error)
        assert "60" in str(error)
        assert "timed out" in str(error).lower()

    def test_error_attributes_accessible(self):
        """TimeoutError attributes are accessible."""
        error = TimeoutError(
            operation_name="my_op",
            timeout_seconds=30.0,
            partial_result={"partial": "data"},
        )

        assert error.operation_name == "my_op"
        assert error.timeout_seconds == 30.0
        assert error.partial_result == {"partial": "data"}
