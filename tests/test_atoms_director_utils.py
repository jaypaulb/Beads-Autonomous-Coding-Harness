"""
Test Atoms: Director Utils
==========================

Tests for director utility atoms (pure functions with no dependencies).
These atoms handle path resolution, validation, and command formatting.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.director.utils import (
    resolve_absolute_path,
    validate_path_is_absolute,
    get_harness_root,
    format_command_for_logging,
)


# =============================================================================
# Tests for resolve_absolute_path()
# =============================================================================


class TestResolveAbsolutePath:
    """Tests for resolve_absolute_path() atom."""

    def test_resolves_string_path_to_absolute(self, tmp_path):
        """resolve_absolute_path() converts string to absolute Path."""
        # Arrange: Create a file in tmp_path
        test_file = tmp_path / "test_file.txt"
        test_file.touch()

        # Act: Use relative-style string (relative to current working)
        # We'll test with the absolute path as string
        result = resolve_absolute_path(str(test_file))

        # Assert
        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == test_file.resolve()

    def test_resolves_path_object_to_absolute(self, tmp_path):
        """resolve_absolute_path() resolves Path object to absolute."""
        # Arrange
        test_file = tmp_path / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        # Act
        result = resolve_absolute_path(test_file)

        # Assert
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_resolves_relative_path_from_string(self):
        """resolve_absolute_path() resolves relative string path."""
        # Arrange
        relative_path = "."

        # Act
        result = resolve_absolute_path(relative_path)

        # Assert
        assert result.is_absolute()
        assert result == Path(".").resolve()

    def test_resolves_path_with_dots(self, tmp_path):
        """resolve_absolute_path() resolves paths containing .. and . components."""
        # Arrange
        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True)
        path_with_dots = subdir / ".." / "b" / "." / ".." / ".."

        # Act
        result = resolve_absolute_path(path_with_dots)

        # Assert
        assert result.is_absolute()
        # Should resolve to tmp_path (a/b/../../.. -> tmp_path)
        assert ".." not in str(result)
        assert result == tmp_path.resolve()


# =============================================================================
# Tests for validate_path_is_absolute()
# =============================================================================


class TestValidatePathIsAbsolute:
    """Tests for validate_path_is_absolute() atom."""

    def test_returns_true_for_absolute_unix_path(self):
        """validate_path_is_absolute() returns True for /absolute/path."""
        # Arrange
        absolute_path = Path("/usr/local/bin")

        # Act
        result = validate_path_is_absolute(absolute_path)

        # Assert
        assert result is True

    def test_returns_false_for_relative_path(self):
        """validate_path_is_absolute() returns False for relative/path."""
        # Arrange
        relative_path = Path("relative/path/to/file")

        # Act
        result = validate_path_is_absolute(relative_path)

        # Assert
        assert result is False

    def test_returns_false_for_dot_relative_path(self):
        """validate_path_is_absolute() returns False for ./relative/path."""
        # Arrange
        dot_relative = Path("./some/path")

        # Act
        result = validate_path_is_absolute(dot_relative)

        # Assert
        assert result is False

    def test_returns_true_for_root_path(self):
        """validate_path_is_absolute() returns True for root path /."""
        # Arrange
        root_path = Path("/")

        # Act
        result = validate_path_is_absolute(root_path)

        # Assert
        assert result is True


# =============================================================================
# Tests for get_harness_root()
# =============================================================================


class TestGetHarnessRoot:
    """Tests for get_harness_root() atom."""

    def test_returns_absolute_path(self):
        """get_harness_root() returns an absolute path."""
        # Act
        result = get_harness_root()

        # Assert
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_returns_existing_directory(self):
        """get_harness_root() returns a path that exists."""
        # Act
        result = get_harness_root()

        # Assert
        assert result.exists()
        assert result.is_dir()

    def test_contains_expected_project_files(self):
        """get_harness_root() returns directory with expected project structure."""
        # Act
        result = get_harness_root()

        # Assert: Should contain key project files/directories
        assert (result / "src").exists() or (result / "tests").exists()


# =============================================================================
# Tests for format_command_for_logging()
# =============================================================================


class TestFormatCommandForLogging:
    """Tests for format_command_for_logging() atom."""

    def test_formats_simple_command(self):
        """format_command_for_logging() joins simple command parts."""
        # Arrange
        cmd = ["git", "status"]

        # Act
        result = format_command_for_logging(cmd)

        # Assert
        assert result == "git status"

    def test_quotes_arguments_with_spaces(self):
        """format_command_for_logging() quotes arguments containing spaces."""
        # Arrange
        cmd = ["git", "commit", "-m", "my commit message"]

        # Act
        result = format_command_for_logging(cmd)

        # Assert
        assert result == 'git commit -m "my commit message"'

    def test_returns_empty_string_for_empty_list(self):
        """format_command_for_logging() returns empty string for empty list."""
        # Arrange
        cmd = []

        # Act
        result = format_command_for_logging(cmd)

        # Assert
        assert result == ""

    def test_handles_mixed_arguments(self):
        """format_command_for_logging() handles mix of quoted and unquoted args."""
        # Arrange
        cmd = ["echo", "hello", "world with spaces", "--flag"]

        # Act
        result = format_command_for_logging(cmd)

        # Assert
        assert result == 'echo hello "world with spaces" --flag'

    def test_converts_non_string_parts_to_strings(self):
        """format_command_for_logging() converts non-string elements to strings."""
        # Arrange
        cmd = ["python", "-c", "print(42)", 123]

        # Act
        result = format_command_for_logging(cmd)

        # Assert
        assert "123" in result
        assert result == "python -c print(42) 123"
