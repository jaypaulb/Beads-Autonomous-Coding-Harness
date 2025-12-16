"""
Test Molecules: Parallel Execution Git Snapshots
=================================================

Tests for parallel execution molecules (snapshot_file_tree).
Molecules compose 2-3 atoms into cohesive units.
Tests focus on composition logic, not atom internals.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.director.parallel_molecules import (
    snapshot_file_tree,
    GitSnapshotError,
    _parse_porcelain_output,
)


class TestSnapshotFileTree:
    """Tests for snapshot_file_tree() molecule."""

    def test_returns_dict_with_required_keys(self, tmp_path):
        """snapshot_file_tree() returns dict with git_status, head_commit, modified_files."""
        # Initialize a git repo in temp directory
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        # Configure git user for the repo
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        result = snapshot_file_tree(tmp_path)

        assert isinstance(result, dict)
        assert "git_status" in result
        assert "head_commit" in result
        assert "modified_files" in result
        # HEAD commit should be 40 char SHA
        assert len(result["head_commit"]) == 40

    def test_captures_modified_files(self, tmp_path):
        """snapshot_file_tree() correctly lists modified files."""
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        # Create and commit initial file
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Modify the file (now it's tracked and modified)
        test_file.write_text("modified content")

        result = snapshot_file_tree(tmp_path)

        assert "test.txt" in result["modified_files"]
        assert "M" in result["git_status"] or " M" in result["git_status"]

    def test_raises_error_for_non_git_directory(self, tmp_path):
        """snapshot_file_tree() raises GitSnapshotError for non-git directory."""
        # tmp_path is not a git repo
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        with pytest.raises(GitSnapshotError) as exc_info:
            snapshot_file_tree(non_git_dir)

        # Error should mention git failure
        assert "git" in str(exc_info.value).lower()

    def test_raises_error_for_nonexistent_directory(self):
        """snapshot_file_tree() raises GitSnapshotError for nonexistent directory."""
        fake_path = Path("/nonexistent/path/that/does/not/exist")

        with pytest.raises(GitSnapshotError) as exc_info:
            snapshot_file_tree(fake_path)

        assert "does not exist" in str(exc_info.value)


class TestParsePorcelainOutput:
    """Tests for _parse_porcelain_output() internal helper."""

    def test_parses_modified_file(self):
        """Parses modified file from porcelain output."""
        output = " M src/file.py\n"
        result = _parse_porcelain_output(output)
        assert result == ["src/file.py"]

    def test_parses_untracked_file(self):
        """Parses untracked file from porcelain output."""
        output = "?? new_file.py\n"
        result = _parse_porcelain_output(output)
        assert result == ["new_file.py"]

    def test_parses_multiple_files(self):
        """Parses multiple files from porcelain output."""
        output = " M file1.py\n?? file2.py\nA  file3.py\n"
        result = _parse_porcelain_output(output)
        assert len(result) == 3
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.py" in result

    def test_handles_empty_output(self):
        """Returns empty list for empty/clean status."""
        result = _parse_porcelain_output("")
        assert result == []

        result = _parse_porcelain_output("   ")
        assert result == []
