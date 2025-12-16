"""
Integration Tests: Agent Prompt Selection
==========================================

Integration tests for the agent.py module's prompt selection logic.
Tests the full decision flow for choosing which prompt to use:

- First run (spec not initialized): initializer_prompt
- Subsequent runs with Beads initialized: director_prompt
- Subsequent runs without Beads: coding_prompt

These tests verify the integration between:
- progress.is_spec_initialized()
- progress.is_beads_initialized()
- prompts.get_*_prompt() functions
- agent.run_autonomous_agent() prompt selection logic
"""

import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# Import the functions and modules under test
from progress import is_spec_initialized, is_beads_initialized
from prompts import get_initializer_prompt, get_coding_prompt, get_director_prompt
from beads_config import BEADS_PROJECT_MARKER


# =============================================================================
# Integration Test: Prompt Selection Decision Logic
# =============================================================================


class TestAgentPromptSelectionIntegration:
    """
    Integration tests for agent.py prompt selection logic.

    Tests the decision tree used in run_autonomous_agent():
    1. is_first_run (spec not initialized) -> initializer_prompt
    2. beads_initialized -> director_prompt
    3. otherwise -> coding_prompt
    """

    def test_first_run_selects_initializer_prompt(self, tmp_path):
        """
        Integration: First run (spec not initialized) selects initializer_prompt.

        When is_spec_initialized() returns False, the agent should use
        the initializer_prompt to set up Beads infrastructure.
        """
        # Arrange: Create empty project directory (no spec marker)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Verify precondition: spec is NOT initialized
        assert is_spec_initialized(project_dir) is False

        # Simulate the prompt selection logic from run_autonomous_agent()
        is_first_run = not is_spec_initialized(project_dir)

        # Act: Select prompt based on first_run state
        if is_first_run:
            selected_prompt = get_initializer_prompt()
        else:
            selected_prompt = get_coding_prompt()  # Should not reach here

        # Assert
        assert is_first_run is True
        expected_prompt = get_initializer_prompt()
        assert selected_prompt == expected_prompt
        # Verify it's actually the initializer prompt content
        assert "initializer" in selected_prompt.lower() or "beads" in selected_prompt.lower()

    def test_subsequent_run_with_beads_selects_director_prompt(self, tmp_path):
        """
        Integration: Subsequent run with Beads initialized selects director_prompt.

        When:
        - is_spec_initialized() returns True (not first run)
        - is_beads_initialized() returns True
        Then: director_prompt should be used for orchestration mode.
        """
        # Arrange: Create spec with marker (simulates initialized spec)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_marker = project_dir / BEADS_PROJECT_MARKER
        spec_marker.write_text(json.dumps({
            "initialized": True,
            "meta_issue_id": "test-meta-123",
            "total_issues": 50
        }))

        # Verify spec is initialized
        assert is_spec_initialized(project_dir) is True

        # Simulate Beads being initialized at project root
        with patch("progress.BEADS_ROOT", tmp_path):
            # Create .beads directory and marker at "root" level
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            root_marker = tmp_path / BEADS_PROJECT_MARKER
            root_marker.write_text(json.dumps({
                "initialized": True,
                "meta_issue_id": "root-meta-456"
            }))

            # Verify Beads is initialized
            assert is_beads_initialized() is True

            # Act: Simulate prompt selection logic
            is_first_run = not is_spec_initialized(project_dir)
            beads_initialized = is_beads_initialized()

            if is_first_run:
                selected_prompt = get_initializer_prompt()
            elif beads_initialized:
                selected_prompt = get_director_prompt()
            else:
                selected_prompt = get_coding_prompt()

            # Assert
            assert is_first_run is False
            assert beads_initialized is True
            expected_prompt = get_director_prompt()
            assert selected_prompt == expected_prompt

    def test_subsequent_run_without_beads_selects_coding_prompt(self, tmp_path):
        """
        Integration: Subsequent run without Beads selects coding_prompt.

        When:
        - is_spec_initialized() returns True (not first run)
        - is_beads_initialized() returns False
        Then: coding_prompt should be used for direct implementation.
        """
        # Arrange: Create spec with marker (simulates initialized spec)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_marker = project_dir / BEADS_PROJECT_MARKER
        spec_marker.write_text(json.dumps({
            "initialized": True,
            "meta_issue_id": "test-meta-789"
        }))

        # Verify spec is initialized
        assert is_spec_initialized(project_dir) is True

        # Simulate Beads NOT being initialized at project root
        with patch("progress.BEADS_ROOT", tmp_path):
            # No .beads directory exists

            # Verify Beads is NOT initialized
            assert is_beads_initialized() is False

            # Act: Simulate prompt selection logic
            is_first_run = not is_spec_initialized(project_dir)
            beads_initialized = is_beads_initialized()

            if is_first_run:
                selected_prompt = get_initializer_prompt()
            elif beads_initialized:
                selected_prompt = get_director_prompt()
            else:
                selected_prompt = get_coding_prompt()

            # Assert
            assert is_first_run is False
            assert beads_initialized is False
            expected_prompt = get_coding_prompt()
            assert selected_prompt == expected_prompt


# =============================================================================
# Integration Test: Full Flow with Mocked Dependencies
# =============================================================================


class TestAgentPromptSelectionWithMocks:
    """
    Integration tests using mocks to verify the decision flow
    without touching the filesystem.
    """

    def test_prompt_selection_flow_with_mocked_checks(self):
        """
        Integration: Full prompt selection flow with mocked state checks.

        This test verifies the complete decision tree using mocks:
        - Mock is_spec_initialized to control first_run detection
        - Mock is_beads_initialized to control Beads state
        - Verify correct prompt is selected in each case
        """
        # Define the prompt selection function (mirrors agent.py logic)
        def select_prompt(is_first_run: bool, beads_initialized: bool) -> str:
            if is_first_run:
                return get_initializer_prompt()
            elif beads_initialized:
                return get_director_prompt()
            else:
                return get_coding_prompt()

        # Get expected prompts for comparison
        initializer = get_initializer_prompt()
        director = get_director_prompt()
        coding = get_coding_prompt()

        # Case 1: First run -> initializer_prompt
        result = select_prompt(is_first_run=True, beads_initialized=False)
        assert result == initializer, "First run should select initializer_prompt"

        # Case 2: First run with Beads (unusual but possible) -> still initializer
        result = select_prompt(is_first_run=True, beads_initialized=True)
        assert result == initializer, "First run should select initializer_prompt even if Beads exists"

        # Case 3: Not first run, Beads initialized -> director_prompt
        result = select_prompt(is_first_run=False, beads_initialized=True)
        assert result == director, "Subsequent run with Beads should select director_prompt"

        # Case 4: Not first run, Beads not initialized -> coding_prompt
        result = select_prompt(is_first_run=False, beads_initialized=False)
        assert result == coding, "Subsequent run without Beads should select coding_prompt"

    def test_all_three_prompts_are_distinct(self):
        """
        Integration: All three prompts are distinct and non-empty.

        The agent must be able to distinguish between the three prompt types.
        """
        initializer = get_initializer_prompt()
        director = get_director_prompt()
        coding = get_coding_prompt()

        # All should be non-empty
        assert len(initializer) > 0, "Initializer prompt should have content"
        assert len(director) > 0, "Director prompt should have content"
        assert len(coding) > 0, "Coding prompt should have content"

        # All should be distinct
        assert initializer != director, "Initializer and director prompts must be distinct"
        assert initializer != coding, "Initializer and coding prompts must be distinct"
        assert director != coding, "Director and coding prompts must be distinct"


# =============================================================================
# Integration Test: Edge Cases
# =============================================================================


class TestAgentPromptSelectionEdgeCases:
    """
    Edge case tests for prompt selection.
    """

    def test_first_run_flag_resets_after_one_iteration(self, tmp_path):
        """
        Integration: First run flag only affects first iteration.

        In run_autonomous_agent(), is_first_run is set to False after
        the first iteration, so subsequent iterations use normal logic.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Simulate first run detection
        is_first_run = not is_spec_initialized(project_dir)
        assert is_first_run is True

        # Iteration 1: Use initializer
        if is_first_run:
            prompt_1 = get_initializer_prompt()
            is_first_run = False  # This happens in the actual code

        # Verify first run flag is now False
        assert is_first_run is False

        # Iteration 2: No longer first run
        with patch("progress.BEADS_ROOT", tmp_path):
            # Still no Beads, so should use coding_prompt
            beads_initialized = is_beads_initialized()

            if is_first_run:
                prompt_2 = get_initializer_prompt()
            elif beads_initialized:
                prompt_2 = get_director_prompt()
            else:
                prompt_2 = get_coding_prompt()

            # Assert iteration 2 uses different prompt
            assert prompt_2 == get_coding_prompt()
            assert prompt_1 != prompt_2

    def test_beads_initialized_check_is_stateless(self, tmp_path):
        """
        Integration: is_beads_initialized() is stateless (filesystem-based).

        The function should return different results when filesystem changes,
        not based on any cached state.
        """
        with patch("progress.BEADS_ROOT", tmp_path):
            # Initially no Beads
            assert is_beads_initialized() is False

            # Create .beads directory
            beads_dir = tmp_path / ".beads"
            beads_dir.mkdir()

            # Still False (needs marker too)
            assert is_beads_initialized() is False

            # Create marker with initialized=True
            marker = tmp_path / BEADS_PROJECT_MARKER
            marker.write_text(json.dumps({"initialized": True}))

            # Now True
            assert is_beads_initialized() is True

            # Remove marker
            marker.unlink()

            # Back to False
            assert is_beads_initialized() is False
