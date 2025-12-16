"""
Test Organisms: Migration and Config Integration
=================================================

Tests for migration script and config integration (organism layer).
These are integration tests that verify composed functionality.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import from scripts
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from migrate_beads import (
    run_bd_command,
    export_issues_from_dir,
    import_issues_to_root,
    delete_beads_dir,
    migrate_beads,
)

# Import from main modules
from progress import (
    detect_rogue_beads_dirs,
    enforce_single_beads_database,
)
from prompts import get_director_prompt
from beads_config import BEADS_ROOT, SPECS_DIR


class TestGetDirectorPrompt:
    """Tests for get_director_prompt() organism in prompts.py."""

    def test_returns_non_empty_string(self):
        """Director prompt is a non-empty string."""
        prompt = get_director_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_contains_director_instructions(self):
        """Director prompt contains expected content."""
        prompt = get_director_prompt()
        # The director prompt should mention delegation or sub-agents
        assert "director" in prompt.lower() or "spawn" in prompt.lower()


class TestEnforceSingleBeadsDatabase:
    """Tests for enforce_single_beads_database() organism in progress.py."""

    def test_passes_when_no_rogue_dirs(self):
        """Does not raise when architecture is correct."""
        # Current state should have no rogue dirs
        enforce_single_beads_database()  # Should not raise

    def test_raises_when_rogue_dirs_exist(self):
        """Raises RuntimeError when spec-level .beads/ exists."""
        # Create a temporary rogue directory
        if SPECS_DIR.exists():
            test_spec_dir = SPECS_DIR / "_test_enforcement_spec"
            rogue_beads_dir = test_spec_dir / ".beads"

            try:
                test_spec_dir.mkdir(exist_ok=True)
                rogue_beads_dir.mkdir(exist_ok=True)

                with pytest.raises(RuntimeError) as excinfo:
                    enforce_single_beads_database()

                assert "Single-database architecture violation" in str(excinfo.value)
                assert str(rogue_beads_dir) in str(excinfo.value)
            finally:
                # Cleanup
                if rogue_beads_dir.exists():
                    rogue_beads_dir.rmdir()
                if test_spec_dir.exists():
                    test_spec_dir.rmdir()


class TestRunBdCommand:
    """Tests for run_bd_command() helper in migrate_beads.py."""

    def test_returns_tuple(self):
        """Returns a (success, output) tuple."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, output = run_bd_command(["echo", "test"], Path(tmpdir))
            assert isinstance(success, bool)
            assert isinstance(output, str)

    def test_captures_stdout(self):
        """Captures command output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, output = run_bd_command(["echo", "hello"], Path(tmpdir))
            assert success is True
            assert "hello" in output

    def test_returns_false_on_failure(self):
        """Returns False for failed commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, output = run_bd_command(
                ["false"],  # Unix command that always fails
                Path(tmpdir)
            )
            assert success is False


class TestMigrateBeadsDryRun:
    """Tests for migrate_beads() dry run mode."""

    def test_dry_run_returns_zero_when_no_rogue_dirs(self):
        """Dry run returns 0 when nothing to migrate."""
        exit_code = migrate_beads(dry_run=True)
        assert exit_code == 0

    def test_dry_run_does_not_modify_filesystem(self):
        """Dry run mode makes no changes."""
        if SPECS_DIR.exists():
            test_spec_dir = SPECS_DIR / "_test_dry_run_spec"
            rogue_beads_dir = test_spec_dir / ".beads"

            try:
                test_spec_dir.mkdir(exist_ok=True)
                rogue_beads_dir.mkdir(exist_ok=True)

                # Run dry run
                migrate_beads(dry_run=True)

                # Directory should still exist
                assert rogue_beads_dir.exists(), "Dry run should not delete directories"
            finally:
                # Cleanup
                if rogue_beads_dir.exists():
                    rogue_beads_dir.rmdir()
                if test_spec_dir.exists():
                    test_spec_dir.rmdir()


class TestDeleteBeadsDir:
    """Tests for delete_beads_dir() helper in migrate_beads.py."""

    def test_dry_run_does_not_delete(self):
        """Dry run mode does not delete directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            beads_dir = Path(tmpdir) / ".beads"
            beads_dir.mkdir()

            success, msg = delete_beads_dir(beads_dir, dry_run=True)

            assert success is True
            assert beads_dir.exists(), "Dry run should not delete"

    def test_actual_delete_removes_directory(self):
        """Actual delete removes the directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            beads_dir = Path(tmpdir) / ".beads"
            beads_dir.mkdir()

            success, msg = delete_beads_dir(beads_dir, dry_run=False)

            assert success is True
            assert not beads_dir.exists(), "Directory should be deleted"
