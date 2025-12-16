"""
Test Atoms: Parallel Execution Utilities
=========================================

Tests for pure parallel execution utility functions (atoms layer).
These are unit tests with no mocking needed - atoms have no dependencies.
"""

from datetime import datetime

import pytest

from src.director.parallel_atoms import (
    sort_by_priority,
    recommend_parallelism,
    create_execution_record,
    calculate_success_rate,
)


class TestSortByPriority:
    """Tests for sort_by_priority() atom."""

    def test_sorts_by_priority_ascending(self):
        """Issues are sorted by priority with P0 first."""
        issues = [
            {"id": "a", "priority": 2},
            {"id": "b", "priority": 0},
            {"id": "c", "priority": 1},
        ]
        result = sort_by_priority(issues)

        assert result[0]["id"] == "b"  # P0 first
        assert result[1]["id"] == "c"  # P1 second
        assert result[2]["id"] == "a"  # P2 third

    def test_does_not_modify_original_list(self):
        """Original list remains unchanged."""
        issues = [{"id": "a", "priority": 2}, {"id": "b", "priority": 0}]
        original_order = [i["id"] for i in issues]

        sort_by_priority(issues)

        assert [i["id"] for i in issues] == original_order

    def test_missing_priority_sorts_last(self):
        """Issues without priority key sort to end."""
        issues = [
            {"id": "no-priority"},
            {"id": "p0", "priority": 0},
            {"id": "p3", "priority": 3},
        ]
        result = sort_by_priority(issues)

        assert result[0]["id"] == "p0"
        assert result[1]["id"] == "p3"
        assert result[2]["id"] == "no-priority"

    def test_empty_list_returns_empty(self):
        """Empty list returns empty list."""
        assert sort_by_priority([]) == []

    def test_single_item_returns_same(self):
        """Single item list returns same item."""
        issues = [{"id": "only", "priority": 2}]
        result = sort_by_priority(issues)
        assert len(result) == 1
        assert result[0]["id"] == "only"


class TestRecommendParallelism:
    """Tests for recommend_parallelism() atom."""

    def test_scales_up_on_high_success(self):
        """Success rate >= 90% increases parallelism."""
        assert recommend_parallelism(0.90, 2) == 3
        assert recommend_parallelism(0.95, 2) == 3
        assert recommend_parallelism(1.0, 2) == 3

    def test_scales_down_on_low_success(self):
        """Success rate < 70% decreases parallelism."""
        assert recommend_parallelism(0.69, 3) == 2
        assert recommend_parallelism(0.50, 3) == 2
        assert recommend_parallelism(0.0, 3) == 2

    def test_maintains_on_medium_success(self):
        """Success rate 70-89% maintains current level."""
        assert recommend_parallelism(0.70, 2) == 2
        assert recommend_parallelism(0.80, 2) == 2
        assert recommend_parallelism(0.89, 2) == 2

    def test_respects_minimum_bound(self):
        """Never goes below 1."""
        assert recommend_parallelism(0.0, 1) == 1  # Would be 0, clamped to 1

    def test_respects_maximum_bound(self):
        """Never goes above 4."""
        assert recommend_parallelism(1.0, 4) == 4  # Would be 5, clamped to 4

    def test_default_current_parallel(self):
        """Default current_parallel is 2."""
        assert recommend_parallelism(0.95) == 3  # 2 + 1


class TestCreateExecutionRecord:
    """Tests for create_execution_record() atom."""

    def test_creates_record_with_all_fields(self):
        """Record contains all required fields."""
        record = create_execution_record(
            parallel_count=3,
            conflicts=1,
            success=True,
            timestamp="2025-01-15T10:30:00",
        )

        assert record["parallel_count"] == 3
        assert record["conflicts"] == 1
        assert record["success"] is True
        assert record["timestamp"] == "2025-01-15T10:30:00"

    def test_auto_generates_timestamp(self):
        """Timestamp is auto-generated if not provided."""
        record = create_execution_record(
            parallel_count=2,
            conflicts=0,
            success=True,
        )

        assert "timestamp" in record
        # Should be ISO format
        datetime.fromisoformat(record["timestamp"])  # Validates format

    def test_success_false_is_preserved(self):
        """Success=False is correctly stored."""
        record = create_execution_record(
            parallel_count=2,
            conflicts=2,
            success=False,
        )

        assert record["success"] is False

    def test_zero_conflicts_is_valid(self):
        """Zero conflicts is a valid value."""
        record = create_execution_record(
            parallel_count=2,
            conflicts=0,
            success=True,
        )

        assert record["conflicts"] == 0


class TestCalculateSuccessRate:
    """Tests for calculate_success_rate() atom."""

    def test_calculates_rate_correctly(self):
        """Calculates correct success rate."""
        executions = [
            {"success": True},
            {"success": True},
            {"success": False},
        ]
        rate = calculate_success_rate(executions)

        assert rate == pytest.approx(2 / 3)  # 0.666...

    def test_empty_list_returns_zero(self):
        """Empty execution list returns 0.0."""
        assert calculate_success_rate([]) == 0.0

    def test_all_success_returns_one(self):
        """All successes returns 1.0."""
        executions = [{"success": True}] * 5
        assert calculate_success_rate(executions) == 1.0

    def test_all_failure_returns_zero(self):
        """All failures returns 0.0."""
        executions = [{"success": False}] * 5
        assert calculate_success_rate(executions) == 0.0

    def test_respects_window_size(self):
        """Only considers last N executions in window."""
        # 5 failures followed by 5 successes
        executions = [{"success": False}] * 5 + [{"success": True}] * 5

        # Window of 5 should only see successes
        rate = calculate_success_rate(executions, window=5)
        assert rate == 1.0

        # Window of 10 should see all
        rate = calculate_success_rate(executions, window=10)
        assert rate == 0.5

    def test_handles_missing_success_key(self):
        """Records without 'success' key are treated as failures."""
        executions = [
            {"success": True},
            {},  # Missing key
            {"success": True},
        ]
        rate = calculate_success_rate(executions)

        assert rate == pytest.approx(2 / 3)
