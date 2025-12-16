"""
Test Improvement Tracker Organism
=================================

Tests for the improvement tracker organism that records execution metrics,
calculates success rates, and recommends parallelism adjustments.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.director.improvement_tracker import (
    record_execution,
    get_success_rate,
    recommend_parallelism,
)
from src.director.metrics_molecules import MetricsData, load_metrics, save_metrics


class TestRecordExecution:
    """Tests for record_execution() organism function."""

    def test_records_execution_to_new_file(self, tmp_path: Path):
        """record_execution() creates metrics file and saves entry."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        start = datetime(2025, 12, 16, 10, 0, 0)
        end = datetime(2025, 12, 16, 10, 5, 30)

        # Act
        result = record_execution(
            issue_id="bd-100",
            agent_type="atom-writer",
            start_time=start,
            end_time=end,
            status="success",
            metrics_file=metrics_file,
        )

        # Assert
        assert result is True
        assert metrics_file.exists()

        loaded = load_metrics(metrics_file)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].issue_id == "bd-100"
        assert loaded[0].agent_type == "atom-writer"
        assert loaded[0].status == "success"
        assert loaded[0].duration == 330.0  # 5 min 30 sec

    def test_records_execution_appends_to_existing(self, tmp_path: Path):
        """record_execution() appends to existing metrics file."""
        # Arrange: Create file with one entry
        metrics_file = tmp_path / "metrics.json"
        existing = [
            MetricsData(
                start_time="2025-12-16T09:00:00",
                end_time="2025-12-16T09:05:00",
                duration=300.0,
                status="success",
                agent_type="molecule-composer",
                issue_id="bd-001",
            ),
        ]
        save_metrics(existing, metrics_file)

        start = datetime(2025, 12, 16, 10, 0, 0)
        end = datetime(2025, 12, 16, 10, 2, 0)

        # Act
        result = record_execution(
            issue_id="bd-002",
            agent_type="atom-writer",
            start_time=start,
            end_time=end,
            status="failure",
            metrics_file=metrics_file,
        )

        # Assert
        assert result is True
        loaded = load_metrics(metrics_file)
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0].issue_id == "bd-001"
        assert loaded[1].issue_id == "bd-002"
        assert loaded[1].status == "failure"

    def test_records_execution_calculates_duration(self, tmp_path: Path):
        """record_execution() correctly calculates duration from timestamps."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        start = datetime(2025, 12, 16, 10, 0, 0)
        end = datetime(2025, 12, 16, 10, 0, 45)  # 45 seconds

        # Act
        record_execution(
            issue_id="bd-103",
            agent_type="atom-writer",
            start_time=start,
            end_time=end,
            status="success",
            metrics_file=metrics_file,
        )

        # Assert
        loaded = load_metrics(metrics_file)
        assert loaded[0].duration == 45.0


class TestGetSuccessRate:
    """Tests for get_success_rate() organism function."""

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        """get_success_rate() returns None when no metrics file exists."""
        # Arrange
        nonexistent = tmp_path / "nonexistent.json"

        # Act
        result = get_success_rate(metrics_file=nonexistent)

        # Assert
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path: Path):
        """get_success_rate() returns None for empty metrics list."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        save_metrics([], metrics_file)

        # Act
        result = get_success_rate(metrics_file=metrics_file)

        # Assert
        assert result is None

    def test_calculates_success_rate_all_success(self, tmp_path: Path):
        """get_success_rate() returns 1.0 when all executions succeeded."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-200",
            ),
            MetricsData(
                start_time="2025-12-16T10:10:00",
                end_time="2025-12-16T10:15:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-201",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act
        result = get_success_rate(metrics_file=metrics_file)

        # Assert
        assert result == 1.0

    def test_calculates_success_rate_all_failure(self, tmp_path: Path):
        """get_success_rate() returns 0.0 when all executions failed."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="failure",
                agent_type="atom-writer",
                issue_id="bd-210",
            ),
            MetricsData(
                start_time="2025-12-16T10:10:00",
                end_time="2025-12-16T10:15:00",
                duration=300.0,
                status="timeout",
                agent_type="atom-writer",
                issue_id="bd-211",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act
        result = get_success_rate(metrics_file=metrics_file)

        # Assert
        assert result == 0.0

    def test_calculates_mixed_success_rate(self, tmp_path: Path):
        """get_success_rate() correctly calculates mixed results."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-220",
            ),
            MetricsData(
                start_time="2025-12-16T10:10:00",
                end_time="2025-12-16T10:15:00",
                duration=300.0,
                status="failure",
                agent_type="atom-writer",
                issue_id="bd-221",
            ),
            MetricsData(
                start_time="2025-12-16T10:20:00",
                end_time="2025-12-16T10:25:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-222",
            ),
            MetricsData(
                start_time="2025-12-16T10:30:00",
                end_time="2025-12-16T10:35:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-223",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act
        result = get_success_rate(metrics_file=metrics_file)

        # Assert: 3 success out of 4 = 0.75
        assert result == 0.75

    def test_filters_by_agent_type(self, tmp_path: Path):
        """get_success_rate() filters by agent_type when specified."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-230",
            ),
            MetricsData(
                start_time="2025-12-16T10:10:00",
                end_time="2025-12-16T10:15:00",
                duration=300.0,
                status="failure",
                agent_type="atom-writer",
                issue_id="bd-231",
            ),
            MetricsData(
                start_time="2025-12-16T10:20:00",
                end_time="2025-12-16T10:25:00",
                duration=300.0,
                status="success",
                agent_type="molecule-composer",
                issue_id="bd-232",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act
        atom_rate = get_success_rate(
            agent_type="atom-writer", metrics_file=metrics_file
        )
        molecule_rate = get_success_rate(
            agent_type="molecule-composer", metrics_file=metrics_file
        )

        # Assert
        assert atom_rate == 0.5  # 1 success out of 2
        assert molecule_rate == 1.0  # 1 success out of 1

    def test_returns_none_when_agent_type_not_found(self, tmp_path: Path):
        """get_success_rate() returns None when no metrics match agent_type."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-240",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act
        result = get_success_rate(
            agent_type="nonexistent-agent", metrics_file=metrics_file
        )

        # Assert
        assert result is None

    def test_filters_by_time_window(self, tmp_path: Path):
        """get_success_rate() filters by time_window_hours when specified."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        now = datetime.now()
        recent = now - timedelta(hours=1)
        old = now - timedelta(hours=25)

        metrics = [
            MetricsData(
                start_time=recent.isoformat(),
                end_time=(recent + timedelta(minutes=5)).isoformat(),
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-250",
            ),
            MetricsData(
                start_time=old.isoformat(),
                end_time=(old + timedelta(minutes=5)).isoformat(),
                duration=300.0,
                status="failure",
                agent_type="atom-writer",
                issue_id="bd-251",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act: Only look at last 24 hours
        result = get_success_rate(time_window_hours=24, metrics_file=metrics_file)

        # Assert: Only the recent success should be counted
        assert result == 1.0

    def test_filters_by_both_agent_type_and_time_window(self, tmp_path: Path):
        """get_success_rate() applies both filters simultaneously."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        now = datetime.now()
        recent = now - timedelta(hours=1)
        old = now - timedelta(hours=25)

        metrics = [
            MetricsData(
                start_time=recent.isoformat(),
                end_time=(recent + timedelta(minutes=5)).isoformat(),
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-260",
            ),
            MetricsData(
                start_time=recent.isoformat(),
                end_time=(recent + timedelta(minutes=5)).isoformat(),
                duration=300.0,
                status="failure",
                agent_type="molecule-composer",
                issue_id="bd-261",
            ),
            MetricsData(
                start_time=old.isoformat(),
                end_time=(old + timedelta(minutes=5)).isoformat(),
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-262",
            ),
        ]
        save_metrics(metrics, metrics_file)

        # Act: atom-writer in last 24 hours
        result = get_success_rate(
            agent_type="atom-writer", time_window_hours=24, metrics_file=metrics_file
        )

        # Assert: Only bd-260 matches (recent + atom-writer)
        assert result == 1.0


class TestRecommendParallelism:
    """Tests for recommend_parallelism() organism function."""

    def test_increases_when_high_success_low_load(self):
        """recommend_parallelism() increases load when success > 80% and load < 3."""
        # Act & Assert
        assert recommend_parallelism(current_load=1, success_rate=0.9) == 2
        assert recommend_parallelism(current_load=2, success_rate=0.85) == 3

    def test_does_not_increase_when_load_at_3_or_higher(self):
        """recommend_parallelism() does not increase when load >= 3."""
        # Act & Assert
        assert recommend_parallelism(current_load=3, success_rate=0.9) == 3
        assert recommend_parallelism(current_load=4, success_rate=0.95) == 4
        assert recommend_parallelism(current_load=5, success_rate=0.99) == 5

    def test_decreases_when_low_success_rate(self):
        """recommend_parallelism() decreases load when success < 50%."""
        # Act & Assert
        assert recommend_parallelism(current_load=3, success_rate=0.4) == 2
        assert recommend_parallelism(current_load=5, success_rate=0.3) == 4
        assert recommend_parallelism(current_load=2, success_rate=0.1) == 1

    def test_minimum_load_is_one(self):
        """recommend_parallelism() never recommends below 1."""
        # Act & Assert
        assert recommend_parallelism(current_load=1, success_rate=0.0) == 1
        assert recommend_parallelism(current_load=1, success_rate=0.2) == 1

    def test_maximum_load_is_five(self):
        """recommend_parallelism() never recommends above 5."""
        # Act & Assert (even if somehow current_load is already > 5)
        assert recommend_parallelism(current_load=10, success_rate=0.9) == 5

    def test_maintains_load_in_middle_range(self):
        """recommend_parallelism() maintains load when 50% <= success <= 80%."""
        # Act & Assert
        assert recommend_parallelism(current_load=2, success_rate=0.5) == 2
        assert recommend_parallelism(current_load=3, success_rate=0.7) == 3
        assert recommend_parallelism(current_load=4, success_rate=0.8) == 4

    def test_maintains_load_when_high_success_but_high_load(self):
        """recommend_parallelism() maintains when success > 80% but load >= 3."""
        # The condition is success > 0.8 AND load < 3 to increase
        # If load >= 3 and success > 0.8, it's stable, not decreased
        assert recommend_parallelism(current_load=3, success_rate=0.85) == 3
        assert recommend_parallelism(current_load=4, success_rate=0.9) == 4

    def test_handles_edge_case_exactly_80_percent(self):
        """recommend_parallelism() treats exactly 80% as 'maintain'."""
        # 0.8 is NOT > 0.8, so it should maintain
        assert recommend_parallelism(current_load=2, success_rate=0.8) == 2

    def test_handles_edge_case_exactly_50_percent(self):
        """recommend_parallelism() treats exactly 50% as 'maintain'."""
        # 0.5 is NOT < 0.5, so it should maintain
        assert recommend_parallelism(current_load=3, success_rate=0.5) == 3

    def test_clamps_invalid_success_rate(self):
        """recommend_parallelism() clamps success_rate to 0-1 range."""
        # Negative rate should be treated as 0
        assert recommend_parallelism(current_load=2, success_rate=-0.5) == 1
        # Rate > 1 should be treated as 1
        assert recommend_parallelism(current_load=1, success_rate=1.5) == 2
