"""
Test Molecules: Metrics Persistence
===================================

Tests for metrics persistence molecules that handle saving and loading
sub-agent execution metrics in JSON format.
"""

import json
from pathlib import Path

import pytest

from src.director.metrics_molecules import (
    MetricsData,
    save_metrics,
    load_metrics,
    append_metrics,
)


class TestMetricsData:
    """Tests for MetricsData dataclass."""

    def test_creates_metrics_data_with_all_fields(self):
        """MetricsData stores all execution metric fields."""
        # Act
        metrics = MetricsData(
            start_time="2025-12-16T10:00:00",
            end_time="2025-12-16T10:05:30",
            duration=330.0,
            status="success",
            agent_type="atom-writer",
            issue_id="bd-123",
        )

        # Assert
        assert metrics.start_time == "2025-12-16T10:00:00"
        assert metrics.end_time == "2025-12-16T10:05:30"
        assert metrics.duration == 330.0
        assert metrics.status == "success"
        assert metrics.agent_type == "atom-writer"
        assert metrics.issue_id == "bd-123"


class TestSaveMetrics:
    """Tests for save_metrics() molecule."""

    def test_saves_metrics_list_to_json_file(self, tmp_path: Path):
        """save_metrics() writes valid JSON to file."""
        # Arrange
        metrics_file = tmp_path / "metrics.json"
        metrics_list = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-100",
            ),
            MetricsData(
                start_time="2025-12-16T10:10:00",
                end_time="2025-12-16T10:15:00",
                duration=300.0,
                status="failure",
                agent_type="molecule-composer",
                issue_id="bd-101",
            ),
        ]

        # Act
        result = save_metrics(metrics_list, metrics_file)

        # Assert
        assert result is True
        assert metrics_file.exists()

        # Verify JSON content
        with open(metrics_file, "r") as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["issue_id"] == "bd-100"
        assert data[1]["issue_id"] == "bd-101"

    def test_creates_parent_directories(self, tmp_path: Path):
        """save_metrics() creates parent directories if needed."""
        # Arrange
        nested_file = tmp_path / "deep" / "nested" / "metrics.json"
        metrics_list = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:01:00",
                duration=60.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-200",
            ),
        ]

        # Act
        result = save_metrics(metrics_list, nested_file)

        # Assert
        assert result is True
        assert nested_file.exists()

    def test_saves_empty_metrics_list(self, tmp_path: Path):
        """save_metrics() handles empty metrics list correctly."""
        # Arrange
        metrics_file = tmp_path / "empty_metrics.json"
        metrics_list = []

        # Act
        result = save_metrics(metrics_list, metrics_file)

        # Assert
        assert result is True
        assert metrics_file.exists()

        # Verify JSON content is empty array
        with open(metrics_file, "r") as f:
            data = json.load(f)

        assert data == []


class TestLoadMetrics:
    """Tests for load_metrics() molecule."""

    def test_loads_metrics_from_valid_json(self, tmp_path: Path):
        """load_metrics() reads back saved metrics correctly."""
        # Arrange: Save metrics first
        metrics_file = tmp_path / "metrics.json"
        original_metrics = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-300",
            ),
        ]
        save_metrics(original_metrics, metrics_file)

        # Act
        loaded = load_metrics(metrics_file)

        # Assert
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].start_time == "2025-12-16T10:00:00"
        assert loaded[0].end_time == "2025-12-16T10:05:00"
        assert loaded[0].duration == 300.0
        assert loaded[0].status == "success"
        assert loaded[0].agent_type == "atom-writer"
        assert loaded[0].issue_id == "bd-300"

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        """load_metrics() returns None when file doesn't exist."""
        # Arrange
        nonexistent_file = tmp_path / "nonexistent.json"

        # Act
        result = load_metrics(nonexistent_file)

        # Assert
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path):
        """load_metrics() returns None for malformed JSON."""
        # Arrange
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ this is not valid json }")

        # Act
        result = load_metrics(invalid_file)

        # Assert
        assert result is None

    def test_loads_empty_metrics_list(self, tmp_path: Path):
        """load_metrics() returns empty list for file containing empty array."""
        # Arrange
        metrics_file = tmp_path / "empty.json"
        metrics_file.write_text("[]")

        # Act
        result = load_metrics(metrics_file)

        # Assert
        assert result is not None
        assert result == []


class TestAppendMetrics:
    """Tests for append_metrics() molecule."""

    def test_appends_to_existing_file(self, tmp_path: Path):
        """append_metrics() adds entry to existing metrics file."""
        # Arrange: Create file with one entry
        metrics_file = tmp_path / "metrics.json"
        initial = [
            MetricsData(
                start_time="2025-12-16T10:00:00",
                end_time="2025-12-16T10:05:00",
                duration=300.0,
                status="success",
                agent_type="atom-writer",
                issue_id="bd-400",
            ),
        ]
        save_metrics(initial, metrics_file)

        # New entry to append
        new_entry = MetricsData(
            start_time="2025-12-16T10:10:00",
            end_time="2025-12-16T10:15:00",
            duration=300.0,
            status="success",
            agent_type="molecule-composer",
            issue_id="bd-401",
        )

        # Act
        result = append_metrics(new_entry, metrics_file)

        # Assert
        assert result is True
        loaded = load_metrics(metrics_file)
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0].issue_id == "bd-400"
        assert loaded[1].issue_id == "bd-401"

    def test_creates_new_file_if_missing(self, tmp_path: Path):
        """append_metrics() creates new file if it doesn't exist."""
        # Arrange
        new_file = tmp_path / "new_metrics.json"
        entry = MetricsData(
            start_time="2025-12-16T10:00:00",
            end_time="2025-12-16T10:05:00",
            duration=300.0,
            status="success",
            agent_type="atom-writer",
            issue_id="bd-500",
        )

        # Act
        result = append_metrics(entry, new_file)

        # Assert
        assert result is True
        assert new_file.exists()
        loaded = load_metrics(new_file)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].issue_id == "bd-500"

    def test_append_to_corrupted_file_creates_fresh_list(self, tmp_path: Path):
        """append_metrics() handles corrupted file by starting fresh list."""
        # Arrange: Create corrupted metrics file
        corrupted_file = tmp_path / "corrupted_metrics.json"
        corrupted_file.write_text("{ not valid json array }")

        new_entry = MetricsData(
            start_time="2025-12-16T10:00:00",
            end_time="2025-12-16T10:05:00",
            duration=300.0,
            status="success",
            agent_type="atom-writer",
            issue_id="bd-600",
        )

        # Act
        result = append_metrics(new_entry, corrupted_file)

        # Assert: Should succeed by creating fresh list with new entry
        assert result is True
        loaded = load_metrics(corrupted_file)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].issue_id == "bd-600"
