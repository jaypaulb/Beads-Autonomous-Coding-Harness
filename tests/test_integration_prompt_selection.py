"""
Integration Tests: Prompt Selection Based on Beads Initialization
===================================================================

Tests that verify the correct prompt is selected based on whether
Beads infrastructure is initialized at the project root.

- Beads initialized (.beads/ exists) -> director_prompt.md
- Beads NOT initialized -> coding_prompt.md
"""

import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the functions under test
from progress import is_beads_initialized, load_beads_project_state
from prompts import get_director_prompt, get_coding_prompt
from beads_config import BEADS_ROOT, BEADS_PROJECT_MARKER


class TestIsBeadsInitializedIntegration:
    """
    Integration test: is_beads_initialized() with real filesystem state.

    This function is the decision point for prompt selection.
    It must correctly detect the presence of .beads/ infrastructure.
    """

    def test_returns_true_when_beads_directory_and_marker_exist(self, tmp_path):
        """
        E2E: is_beads_initialized returns True when .beads/ and marker exist.

        This is the "Beads initialized" state where director_prompt should be used.
        """
        # Patch BEADS_ROOT to use tmp_path for isolation
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create .beads directory and valid marker
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            marker_file = tmp_path / BEADS_PROJECT_MARKER
            marker_file.write_text(json.dumps({
                "initialized": True,
                "meta_issue_id": "test-123",
                "total_issues": 10
            }))

            result = is_beads_initialized()

            assert result is True, (
                "Should return True when .beads/ exists and marker has initialized=True"
            )

    def test_returns_false_when_beads_directory_missing(self, tmp_path):
        """
        E2E: is_beads_initialized returns False when .beads/ doesn't exist.

        This is the "Beads NOT initialized" state where coding_prompt should be used.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # Don't create .beads directory - simulate fresh project
            result = is_beads_initialized()

            assert result is False, (
                "Should return False when .beads/ directory doesn't exist"
            )

    def test_returns_false_when_marker_missing(self, tmp_path):
        """
        E2E: is_beads_initialized returns False when marker file is missing.

        Having .beads/ but no marker means initialization is incomplete.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create .beads directory but no marker
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            result = is_beads_initialized()

            assert result is False, (
                "Should return False when .beads/ exists but marker is missing"
            )

    def test_returns_false_when_initialized_flag_false(self, tmp_path):
        """
        E2E: is_beads_initialized returns False when initialized=False in marker.

        The marker must explicitly have initialized=True.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create .beads directory and marker with initialized=False
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            marker_file = tmp_path / BEADS_PROJECT_MARKER
            marker_file.write_text(json.dumps({
                "initialized": False,
                "meta_issue_id": None
            }))

            result = is_beads_initialized()

            assert result is False, (
                "Should return False when marker has initialized=False"
            )


class TestPromptSelectionLogic:
    """
    Integration test: Prompt selection based on Beads initialization state.

    Verifies that:
    - director_prompt is selected when Beads IS initialized
    - coding_prompt is selected when Beads is NOT initialized
    """

    def test_director_prompt_selected_when_beads_initialized(self, tmp_path):
        """
        E2E: When Beads is initialized, director_prompt.md content is returned.

        The director prompt orchestrates multiple agents via Beads issues.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create initialized Beads state
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            marker_file = tmp_path / BEADS_PROJECT_MARKER
            marker_file.write_text(json.dumps({
                "initialized": True,
                "meta_issue_id": "test-123",
                "total_issues": 50
            }))

            # Verify Beads is considered initialized
            assert is_beads_initialized() is True

            # In this state, director_prompt should be selected
            director_content = get_director_prompt()

            # Verify we got director prompt content (check for distinctive content)
            assert "director" in director_content.lower() or "orchestrat" in director_content.lower(), (
                "Director prompt should contain director/orchestration terminology"
            )

    def test_coding_prompt_selected_when_beads_not_initialized(self, tmp_path):
        """
        E2E: When Beads is NOT initialized, coding_prompt.md content is returned.

        The coding prompt handles direct implementation without Beads orchestration.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # No .beads directory - fresh project

            # Verify Beads is NOT initialized
            assert is_beads_initialized() is False

            # In this state, coding_prompt should be selected
            coding_content = get_coding_prompt()

            # Verify we got coding prompt content
            assert len(coding_content) > 0, "Coding prompt should have content"

    def test_prompt_selection_function_integration(self, tmp_path):
        """
        E2E: Full integration of prompt selection decision logic.

        This test simulates the actual decision flow that will be used
        in run_autonomous_agent().
        """
        def select_prompt_based_on_beads() -> str:
            """
            Prompt selection logic matching run_autonomous_agent requirements.

            Returns director_prompt if Beads initialized, coding_prompt otherwise.
            """
            if is_beads_initialized():
                return get_director_prompt()
            else:
                return get_coding_prompt()

        # Test 1: Fresh project (no Beads) -> coding_prompt
        with patch("progress.BEADS_ROOT", tmp_path):
            selected = select_prompt_based_on_beads()
            coding = get_coding_prompt()

            assert selected == coding, (
                "Fresh project should select coding_prompt"
            )

        # Test 2: Initialized project -> director_prompt
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create initialized state
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            marker_file = tmp_path / BEADS_PROJECT_MARKER
            marker_file.write_text(json.dumps({
                "initialized": True,
                "meta_issue_id": "test-123"
            }))

            selected = select_prompt_based_on_beads()
            director = get_director_prompt()

            assert selected == director, (
                "Initialized project should select director_prompt"
            )


class TestPromptContentValidity:
    """
    Integration test: Verify prompt files exist and contain expected content.

    Ensures the prompt files referenced in selection logic actually exist
    and contain meaningful content.
    """

    def test_director_prompt_file_exists_and_loads(self):
        """
        E2E: director_prompt.md exists and can be loaded.
        """
        content = get_director_prompt()

        assert isinstance(content, str), "Prompt should be a string"
        assert len(content) > 100, "Director prompt should have substantial content"

    def test_coding_prompt_file_exists_and_loads(self):
        """
        E2E: coding_prompt.md exists and can be loaded.
        """
        content = get_coding_prompt()

        assert isinstance(content, str), "Prompt should be a string"
        assert len(content) > 100, "Coding prompt should have substantial content"

    def test_prompts_are_distinct(self):
        """
        E2E: Director and coding prompts are different content.

        They serve different purposes and must be distinct.
        """
        director = get_director_prompt()
        coding = get_coding_prompt()

        assert director != coding, (
            "Director and coding prompts must be distinct"
        )
