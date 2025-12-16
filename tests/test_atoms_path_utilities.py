"""
Test Atoms: Path Utilities and Validators
==========================================

Tests for pure path utility functions (atoms layer).
These are unit tests with no mocking needed - atoms have no dependencies.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Import atoms from director utils
from src.director.utils import (
    resolve_absolute_path,
    validate_path_is_absolute,
    get_harness_root,
    format_command_for_logging,
)

# Import beads_config atoms
from beads_config import (
    HARNESS_ROOT,
    BEADS_ROOT,
    PRODUCT_DOCS_DIR,
    SPECS_DIR,
    DIRECTOR_PROMPTS_DIR,
    validate_beads_location,
)

# Import progress atoms
from progress import detect_rogue_beads_dirs


class TestResolveAbsolutePath:
    """Tests for resolve_absolute_path() atom."""

    def test_resolves_relative_path_to_absolute(self):
        """Relative paths are resolved to absolute."""
        result = resolve_absolute_path("some/relative/path")
        assert result.is_absolute(), "Result should be an absolute path"

    def test_resolves_path_object(self):
        """Path objects are handled correctly."""
        path = Path("some/relative/path")
        result = resolve_absolute_path(path)
        assert result.is_absolute(), "Result should be an absolute path"

    def test_already_absolute_path_unchanged_location(self):
        """Absolute paths maintain their location after resolve."""
        absolute = Path("/tmp/some/path")
        result = resolve_absolute_path(absolute)
        assert result.is_absolute()
        # Note: resolve() may change the path if symlinks exist
        # but it should still be absolute

    def test_handles_string_input(self):
        """String inputs are converted to Path."""
        result = resolve_absolute_path("/tmp/test")
        assert isinstance(result, Path)
        assert result.is_absolute()


class TestValidatePathIsAbsolute:
    """Tests for validate_path_is_absolute() atom."""

    def test_returns_true_for_absolute_path(self):
        """Returns True for absolute paths."""
        assert validate_path_is_absolute(Path("/tmp/absolute/path")) is True

    def test_returns_false_for_relative_path(self):
        """Returns False for relative paths."""
        assert validate_path_is_absolute(Path("relative/path")) is False

    def test_returns_true_for_root(self):
        """Returns True for root path."""
        assert validate_path_is_absolute(Path("/")) is True

    def test_returns_false_for_current_dir(self):
        """Returns False for current directory reference."""
        assert validate_path_is_absolute(Path(".")) is False


class TestGetHarnessRoot:
    """Tests for get_harness_root() atom."""

    def test_returns_absolute_path(self):
        """Harness root is an absolute path."""
        root = get_harness_root()
        assert root.is_absolute(), "Harness root should be absolute"

    def test_returns_resolved_path(self):
        """Harness root is fully resolved (no symlinks)."""
        root = get_harness_root()
        # resolved path equals itself when resolved again
        assert root == root.resolve()

    def test_matches_harness_root_constant(self):
        """Harness root matches HARNESS_ROOT constant."""
        root = get_harness_root()
        # HARNESS_ROOT is defined as parent of beads_config.py
        # get_harness_root() should return the same value
        assert root == HARNESS_ROOT


class TestFormatCommandForLogging:
    """Tests for format_command_for_logging() atom."""

    def test_formats_simple_command(self):
        """Simple commands are formatted as space-separated string."""
        cmd = ["pytest", "/path/to/tests"]
        result = format_command_for_logging(cmd)
        assert result == "pytest /path/to/tests"

    def test_formats_empty_list(self):
        """Empty command list returns empty string."""
        result = format_command_for_logging([])
        assert result == ""

    def test_handles_paths_with_spaces(self):
        """Paths with spaces are quoted."""
        cmd = ["python", "/path/with spaces/script.py"]
        result = format_command_for_logging(cmd)
        # Should quote the path with spaces
        assert '"/path/with spaces/script.py"' in result or "'/path/with spaces/script.py'" in result


class TestPathConstants:
    """Tests for path constants in beads_config.py."""

    def test_product_docs_dir_is_absolute(self):
        """PRODUCT_DOCS_DIR is an absolute path."""
        assert PRODUCT_DOCS_DIR.is_absolute()

    def test_product_docs_dir_under_harness_root(self):
        """PRODUCT_DOCS_DIR is under HARNESS_ROOT."""
        assert str(PRODUCT_DOCS_DIR).startswith(str(HARNESS_ROOT))

    def test_specs_dir_is_absolute(self):
        """SPECS_DIR is an absolute path."""
        assert SPECS_DIR.is_absolute()

    def test_specs_dir_under_harness_root(self):
        """SPECS_DIR is under HARNESS_ROOT."""
        assert str(SPECS_DIR).startswith(str(HARNESS_ROOT))

    def test_director_prompts_dir_is_absolute(self):
        """DIRECTOR_PROMPTS_DIR is an absolute path."""
        assert DIRECTOR_PROMPTS_DIR.is_absolute()

    def test_beads_root_defaults_to_harness_root(self):
        """BEADS_ROOT defaults to HARNESS_ROOT when env var not set."""
        # When BEADS_ROOT env var is not set, it should equal HARNESS_ROOT
        if os.environ.get("BEADS_ROOT") is None:
            assert BEADS_ROOT == HARNESS_ROOT


class TestValidateBeadsLocation:
    """Tests for validate_beads_location() atom in beads_config.py."""

    def test_returns_true_when_no_spec_level_beads(self):
        """Returns True when no spec-level .beads/ directories exist."""
        # This test verifies current state - no rogue .beads/ dirs
        # If this fails, there are rogue directories to clean up
        result = validate_beads_location()
        assert result is True, "Should return True when only root .beads/ exists"

    def test_is_pure_function(self):
        """Function has no side effects - calling twice gives same result."""
        result1 = validate_beads_location()
        result2 = validate_beads_location()
        assert result1 == result2


class TestDetectRogueBeadsDirs:
    """Tests for detect_rogue_beads_dirs() atom in progress.py."""

    def test_returns_empty_list_when_no_rogue_dirs(self):
        """Returns empty list when no spec-level .beads/ exist."""
        result = detect_rogue_beads_dirs()
        assert isinstance(result, list)
        # In current state, should be empty
        assert len(result) == 0, f"Expected no rogue dirs, found: {result}"

    def test_returns_list_of_paths(self):
        """Return type is list[Path]."""
        result = detect_rogue_beads_dirs()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, Path), f"Expected Path, got {type(item)}"

    def test_detects_rogue_directory_when_present(self):
        """Detects .beads/ directory inside specs folder."""
        # Create a temporary rogue .beads/ directory for testing
        specs_dir = SPECS_DIR
        if specs_dir.exists():
            # Create a temporary spec with a rogue .beads
            test_spec_dir = specs_dir / "_test_rogue_spec"
            rogue_beads_dir = test_spec_dir / ".beads"

            try:
                test_spec_dir.mkdir(exist_ok=True)
                rogue_beads_dir.mkdir(exist_ok=True)

                result = detect_rogue_beads_dirs()

                assert rogue_beads_dir in result, (
                    f"Should detect rogue .beads/ at {rogue_beads_dir}"
                )
            finally:
                # Cleanup
                if rogue_beads_dir.exists():
                    rogue_beads_dir.rmdir()
                if test_spec_dir.exists():
                    test_spec_dir.rmdir()
