"""
Test Molecules: Spawn Helpers
==============================

Tests for composed helper functions for sub-agent spawning (molecules layer).
These molecules compose 2-3 atoms into cohesive units for:
- Loading agent files with priority cascade
- Loading issue data from Beads CLI
- Building delegation context for sub-agents
"""

import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

# Molecules to be implemented in src/director/spawn_molecules.py
from src.director.spawn_molecules import (
    load_agent_file,
    load_issue_from_beads,
    build_delegation_context,
)


class TestLoadAgentFile:
    """Tests for load_agent_file() molecule.

    This molecule composes atoms:
    - resolve_agent_path() - path resolution
    - extract_yaml_frontmatter() - YAML parsing
    - extract_agent_prompt() - content extraction
    """

    def test_loads_local_agent_file_with_frontmatter(self, tmp_path: Path):
        """load_agent_file() loads agent from local .claude/agents/agent-os/ path."""
        # Arrange: Create local agent file with frontmatter
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
model: sonnet
tools: Read, Write
---
# Test Agent Instructions
Do the test things.""")

        # Act
        path, frontmatter, prompt = load_agent_file("test-agent", tmp_path)

        # Assert
        assert path == agent_file
        assert frontmatter["model"] == "sonnet"
        assert "# Test Agent Instructions" in prompt
        assert "Do the test things." in prompt

    def test_falls_back_to_implementer_when_agent_not_found(self, tmp_path: Path):
        """load_agent_file() falls back to implementer.md when requested agent missing."""
        # Arrange: Create only implementer fallback, not the requested agent
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        fallback_file = agents_dir / "implementer.md"
        fallback_file.write_text("""---
model: sonnet
---
# Implementer Agent
Default implementation agent.""")

        # Act: Request nonexistent agent
        path, frontmatter, prompt = load_agent_file("nonexistent-agent", tmp_path)

        # Assert: Should fall back to implementer
        assert path == fallback_file
        assert "# Implementer Agent" in prompt

    def test_raises_file_not_found_when_no_fallback(self, tmp_path: Path):
        """load_agent_file() raises FileNotFoundError when agent and fallback both missing."""
        # Arrange: Empty directory, no agents at all

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            load_agent_file("missing-agent", tmp_path, master_dir=tmp_path)

        assert "missing-agent" in str(exc_info.value)


class TestLoadIssueFromBeads:
    """Tests for load_issue_from_beads() molecule.

    This molecule executes the bd CLI and parses JSON output.
    """

    @patch("src.director.spawn_molecules.subprocess.run")
    def test_loads_issue_data_from_bd_cli(self, mock_run: patch, tmp_path: Path):
        """load_issue_from_beads() parses bd show --json output correctly."""
        # Arrange: Mock successful bd show response
        mock_run.return_value = CompletedProcess(
            args=["bd", "show", "bd-123", "--json"],
            returncode=0,
            stdout=json.dumps({
                "id": "bd-123",
                "title": "Test Issue Title",
                "description": "Issue description here",
                "tags": ["test", "molecule"],
                "priority": 1,
                "assignee": "atom-writer",
                "status": "open"
            })
        )

        # Act
        issue = load_issue_from_beads("bd-123", tmp_path)

        # Assert
        assert issue is not None
        assert issue["id"] == "bd-123"
        assert issue["title"] == "Test Issue Title"
        assert issue["priority"] == 1
        assert "test" in issue["tags"]

    @patch("src.director.spawn_molecules.subprocess.run")
    def test_returns_none_when_bd_command_fails(self, mock_run: patch, tmp_path: Path):
        """load_issue_from_beads() returns None when bd show fails."""
        # Arrange: Mock failed bd command
        mock_run.return_value = CompletedProcess(
            args=["bd", "show", "bd-999", "--json"],
            returncode=1,
            stdout="",
            stderr="Issue not found"
        )

        # Act
        issue = load_issue_from_beads("bd-999", tmp_path)

        # Assert
        assert issue is None


class TestBuildDelegationContext:
    """Tests for build_delegation_context() molecule.

    This molecule formats issue data and agent prompt into delegation context.
    """

    def test_builds_context_with_all_issue_fields(self):
        """build_delegation_context() includes issue id, title, description, tags, priority."""
        # Arrange
        issue = {
            "id": "bd-100",
            "title": "Implement Feature X",
            "description": "Add new feature X to the system",
            "tags": ["feature", "high-priority"],
            "priority": "P1"
        }

        # Act
        context = build_delegation_context(
            issue=issue,
            agent_prompt="You are a helpful coding agent.",
            task_instructions="Complete this feature implementation."
        )

        # Assert: All issue fields present
        assert "bd-100" in context
        assert "Implement Feature X" in context
        assert "Add new feature X to the system" in context
        assert "feature" in context
        assert "P1" in context
        # Agent prompt and instructions included
        assert "You are a helpful coding agent." in context
        assert "Complete this feature implementation." in context

    def test_includes_beads_workflow_commands(self):
        """build_delegation_context() includes bd update and bd close commands."""
        # Arrange
        issue = {"id": "bd-42", "title": "Test", "description": "", "tags": [], "priority": 2}

        # Act
        context = build_delegation_context(
            issue=issue,
            agent_prompt="Agent prompt here.",
            task_instructions="Task instructions here."
        )

        # Assert: Workflow commands present
        assert "bd update bd-42 --status in_progress" in context
        assert "bd close bd-42" in context
