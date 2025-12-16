"""
Timeout Organisms - Async Timeout Handling
==========================================

Organism for wrapping async operations with timeout handling.
Composes timeout constants with asyncio.timeout for robust
sub-agent execution control.

This organism provides:
- Configurable timeout wrapping for any async operation
- Proper cleanup on timeout (task cancellation)
- Logging of timeout events for observability
- Graceful degradation with detailed error information
"""

import asyncio
import logging
from typing import TypeVar, Callable, Awaitable, Optional, Any

from .timeout_atoms import (
    DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    CLEANUP_GRACE_PERIOD_SECONDS,
)

# Configure module logger
logger = logging.getLogger(__name__)

# Type variable for generic async return type
T = TypeVar("T")


class TimeoutError(Exception):
    """
    Custom timeout error with context about what timed out.

    Attributes:
        operation_name: Name/description of the operation that timed out
        timeout_seconds: The timeout value that was exceeded
        partial_result: Any partial result available before timeout
    """

    def __init__(
        self,
        operation_name: str,
        timeout_seconds: float,
        partial_result: Any = None,
    ):
        self.operation_name = operation_name
        self.timeout_seconds = timeout_seconds
        self.partial_result = partial_result
        super().__init__(
            f"Operation '{operation_name}' timed out after {timeout_seconds} seconds"
        )


class TimeoutResult:
    """
    Result container for timeout-wrapped operations.

    Provides a consistent interface for handling both successful
    completions and timeouts without exceptions.

    Attributes:
        success: Whether the operation completed successfully
        result: The operation result (if successful)
        timed_out: Whether the operation timed out
        error: Any error that occurred (timeout or other)
        elapsed_seconds: How long the operation ran
    """

    def __init__(
        self,
        success: bool,
        result: Any = None,
        timed_out: bool = False,
        error: Optional[Exception] = None,
        elapsed_seconds: float = 0.0,
    ):
        self.success = success
        self.result = result
        self.timed_out = timed_out
        self.error = error
        self.elapsed_seconds = elapsed_seconds

    def __repr__(self) -> str:
        if self.success:
            return f"TimeoutResult(success=True, elapsed={self.elapsed_seconds:.2f}s)"
        elif self.timed_out:
            return f"TimeoutResult(timed_out=True, elapsed={self.elapsed_seconds:.2f}s)"
        else:
            return f"TimeoutResult(error={self.error}, elapsed={self.elapsed_seconds:.2f}s)"


async def run_with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float = DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    operation_name: str = "async_operation",
    cleanup_callback: Optional[Callable[[], Awaitable[None]]] = None,
    raise_on_timeout: bool = True,
) -> T | TimeoutResult:
    """
    Execute an async operation with timeout handling.

    This organism wraps any awaitable with asyncio.timeout and provides:
    - Configurable timeout duration
    - Optional cleanup callback on timeout
    - Logging of timeout events
    - Choice between raising exception or returning result object

    Args:
        coro: The awaitable to execute (coroutine or task)
        timeout_seconds: Maximum time to wait for completion
        operation_name: Descriptive name for logging and errors
        cleanup_callback: Optional async function to call on timeout
        raise_on_timeout: If True, raises TimeoutError; if False, returns TimeoutResult

    Returns:
        If raise_on_timeout=True: Returns the coroutine result or raises TimeoutError
        If raise_on_timeout=False: Returns TimeoutResult with success/failure info

    Raises:
        TimeoutError: If operation times out and raise_on_timeout=True
        Exception: Any exception from the coroutine is re-raised

    Example:
        # Simple usage with exception on timeout
        result = await run_with_timeout(
            some_async_operation(),
            timeout_seconds=60,
            operation_name="fetch_data"
        )

        # With cleanup callback
        async def cleanup():
            await cancel_pending_work()

        result = await run_with_timeout(
            long_running_task(),
            timeout_seconds=300,
            cleanup_callback=cleanup
        )

        # Without raising, check result object
        result = await run_with_timeout(
            risky_operation(),
            raise_on_timeout=False
        )
        if result.timed_out:
            handle_timeout(result)
    """
    import time
    start_time = time.monotonic()

    logger.debug(
        f"Starting operation '{operation_name}' with {timeout_seconds}s timeout"
    )

    try:
        # Use asyncio.timeout context manager (Python 3.11+)
        async with asyncio.timeout(timeout_seconds):
            result = await coro

        elapsed = time.monotonic() - start_time
        logger.debug(
            f"Operation '{operation_name}' completed successfully in {elapsed:.2f}s"
        )

        if raise_on_timeout:
            return result
        else:
            return TimeoutResult(
                success=True,
                result=result,
                elapsed_seconds=elapsed,
            )

    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start_time
        logger.warning(
            f"Operation '{operation_name}' timed out after {elapsed:.2f}s "
            f"(limit: {timeout_seconds}s)"
        )

        # Run cleanup callback if provided
        if cleanup_callback is not None:
            logger.debug(f"Running cleanup callback for '{operation_name}'")
            try:
                # Give cleanup a grace period to complete
                async with asyncio.timeout(CLEANUP_GRACE_PERIOD_SECONDS):
                    await cleanup_callback()
                logger.debug(f"Cleanup completed for '{operation_name}'")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Cleanup callback for '{operation_name}' also timed out"
                )
            except Exception as cleanup_error:
                logger.error(
                    f"Cleanup callback for '{operation_name}' failed: {cleanup_error}"
                )

        if raise_on_timeout:
            raise TimeoutError(
                operation_name=operation_name,
                timeout_seconds=timeout_seconds,
            )
        else:
            return TimeoutResult(
                success=False,
                timed_out=True,
                error=TimeoutError(operation_name, timeout_seconds),
                elapsed_seconds=elapsed,
            )

    except asyncio.CancelledError:
        # Task was cancelled externally - re-raise to preserve semantics
        elapsed = time.monotonic() - start_time
        logger.info(
            f"Operation '{operation_name}' was cancelled after {elapsed:.2f}s"
        )
        raise

    except Exception as e:
        # Other exceptions - log and re-raise or return in result
        elapsed = time.monotonic() - start_time
        logger.error(
            f"Operation '{operation_name}' failed after {elapsed:.2f}s: {e}"
        )

        if raise_on_timeout:
            raise
        else:
            return TimeoutResult(
                success=False,
                timed_out=False,
                error=e,
                elapsed_seconds=elapsed,
            )


async def run_with_timeout_and_cancel(
    task: asyncio.Task[T],
    timeout_seconds: float = DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    operation_name: str = "async_task",
) -> TimeoutResult:
    """
    Execute an asyncio Task with timeout and automatic cancellation on timeout.

    This variant is specifically for asyncio.Task objects where we want
    to cancel the task if it times out. The task cancellation is handled
    internally with proper cleanup.

    Args:
        task: The asyncio.Task to execute
        timeout_seconds: Maximum time to wait for completion
        operation_name: Descriptive name for logging

    Returns:
        TimeoutResult with success/failure info

    Note:
        Unlike run_with_timeout(), this function always returns TimeoutResult
        and never raises TimeoutError, as the primary use case is for
        parallel task management where we want to handle failures gracefully.

    Example:
        task = asyncio.create_task(subagent_work())
        result = await run_with_timeout_and_cancel(task, timeout_seconds=600)

        if result.timed_out:
            log_timeout(result)
        elif result.success:
            process_result(result.result)
    """
    import time
    start_time = time.monotonic()

    logger.debug(
        f"Monitoring task '{operation_name}' with {timeout_seconds}s timeout"
    )

    try:
        async with asyncio.timeout(timeout_seconds):
            result = await task

        elapsed = time.monotonic() - start_time
        logger.debug(
            f"Task '{operation_name}' completed successfully in {elapsed:.2f}s"
        )

        return TimeoutResult(
            success=True,
            result=result,
            elapsed_seconds=elapsed,
        )

    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start_time
        logger.warning(
            f"Task '{operation_name}' timed out after {elapsed:.2f}s - cancelling"
        )

        # Cancel the task
        task.cancel()

        # Wait for cancellation to complete (with grace period)
        try:
            async with asyncio.timeout(CLEANUP_GRACE_PERIOD_SECONDS):
                await task
        except asyncio.CancelledError:
            logger.debug(f"Task '{operation_name}' cancelled successfully")
        except asyncio.TimeoutError:
            logger.warning(
                f"Task '{operation_name}' did not respond to cancellation"
            )
        except Exception as e:
            # Task raised an exception during cancellation - log it
            logger.debug(
                f"Task '{operation_name}' raised during cancellation: {e}"
            )

        return TimeoutResult(
            success=False,
            timed_out=True,
            error=TimeoutError(operation_name, timeout_seconds),
            elapsed_seconds=elapsed,
        )

    except asyncio.CancelledError:
        elapsed = time.monotonic() - start_time
        logger.info(
            f"Task '{operation_name}' was externally cancelled after {elapsed:.2f}s"
        )
        return TimeoutResult(
            success=False,
            timed_out=False,
            error=asyncio.CancelledError(),
            elapsed_seconds=elapsed,
        )

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            f"Task '{operation_name}' failed after {elapsed:.2f}s: {e}"
        )

        return TimeoutResult(
            success=False,
            timed_out=False,
            error=e,
            elapsed_seconds=elapsed,
        )
