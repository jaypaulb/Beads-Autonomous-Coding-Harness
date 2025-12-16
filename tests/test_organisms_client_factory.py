"""
Test Organisms: Sub-Agent Client Factory
==========================================

Tests for the client factory organism that creates restricted Claude SDK
clients with tool restrictions from agent frontmatter.

These are organism-level integration tests that verify the full client
creation workflow including security settings and tool restrictions.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the organism to be implemented
from src.director.client_factory import (
    create_subagent_client,
    build_security_settings,
    parse_tools_from_frontmatter,
    DEFAULT_TOOLS,
    DEFAULT_MCP_SERVERS,
)


class TestParseToolsFromFrontmatter:
    """Tests for parse_tools_from_frontmatter() helper.

    This atom parses the 'tools' field from agent frontmatter
    into a list of tool names.
    """

    def test_parses_comma_separated_tools(self):
        """Comma-separated tools are parsed into a list."""
        frontmatter = {"tools": "Read, Write, Bash"}
        result = parse_tools_from_frontmatter(frontmatter)
        assert result == ["Read", "Write", "Bash"]

    def test_returns_defaults_when_tools_missing(self):
        """Returns default tools when 'tools' key is missing."""
        frontmatter = {"model": "sonnet"}
        result = parse_tools_from_frontmatter(frontmatter)
        assert result == list(DEFAULT_TOOLS)

    def test_strips_whitespace_from_tool_names(self):
        """Whitespace is stripped from individual tool names."""
        frontmatter = {"tools": "  Read  ,   Write  ,Bash"}
        result = parse_tools_from_frontmatter(frontmatter)
        assert result == ["Read", "Write", "Bash"]

    def test_handles_empty_tools_string(self):
        """Empty tools string returns empty list, not defaults."""
        frontmatter = {"tools": ""}
        result = parse_tools_from_frontmatter(frontmatter)
        assert result == []

    def test_handles_single_tool(self):
        """Single tool without comma is parsed correctly."""
        frontmatter = {"tools": "Read"}
        result = parse_tools_from_frontmatter(frontmatter)
        assert result == ["Read"]


class TestBuildSecuritySettings:
    """Tests for build_security_settings() helper.

    This molecule builds the security settings dict for a sub-agent
    with restricted tool permissions.
    """

    def test_includes_sandbox_settings(self):
        """Security settings include sandbox configuration."""
        settings = build_security_settings(["Read", "Write"], Path("/tmp/project"))
        assert "sandbox" in settings
        assert settings["sandbox"]["enabled"] is True

    def test_includes_permissions_for_tools(self):
        """Security settings include permission entries for each tool."""
        settings = build_security_settings(["Read", "Write", "Bash"], Path("/tmp/project"))
        assert "permissions" in settings
        allow_list = settings["permissions"]["allow"]
        # Should have Read, Write, and Bash permissions
        assert any("Read" in perm for perm in allow_list)
        assert any("Write" in perm for perm in allow_list)
        assert any("Bash" in perm for perm in allow_list)

    def test_restricts_file_tools_to_project_dir(self):
        """File tools are restricted to project directory via glob patterns."""
        settings = build_security_settings(["Read", "Write", "Glob"], Path("/tmp/project"))
        allow_list = settings["permissions"]["allow"]
        # File tools should use relative path pattern
        assert "Read(./**)" in allow_list
        assert "Write(./**)" in allow_list
        assert "Glob(./**)" in allow_list

    def test_bash_uses_wildcard(self):
        """Bash permission uses wildcard (validation via hook)."""
        settings = build_security_settings(["Bash"], Path("/tmp/project"))
        allow_list = settings["permissions"]["allow"]
        assert "Bash(*)" in allow_list

    def test_excludes_tools_not_in_list(self):
        """Tools not in the allowed list are excluded from permissions."""
        settings = build_security_settings(["Read"], Path("/tmp/project"))
        allow_list = settings["permissions"]["allow"]
        # Write and Bash should NOT be in permissions
        assert not any("Write" in perm for perm in allow_list if "Write" in perm.split("(")[0])
        assert not any("Bash" in perm for perm in allow_list if "Bash" in perm.split("(")[0])


class TestCreateSubagentClient:
    """Tests for create_subagent_client() organism.

    This organism creates a fully configured Claude SDK client
    for sub-agents with restricted tool access based on frontmatter.
    """

    def test_creates_client_with_restricted_tools(self, tmp_path: Path):
        """Client is created with only the tools from frontmatter."""
        # Arrange: Create agent file with restricted tools
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
model: sonnet
tools: Read, Write
---
# Test Agent
You are a test agent.""")

        with patch("src.director.client_factory.ClaudeSDKClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Act
            client, frontmatter = create_subagent_client(
                agent_name="test-agent",
                project_dir=tmp_path,
                model="sonnet"
            )

            # Assert: Client was created
            assert mock_client_class.called
            call_kwargs = mock_client_class.call_args

            # Extract the options from the call
            options = call_kwargs[1].get("options") or call_kwargs[0][0]

            # Verify allowed_tools only has Read and Write
            assert "Read" in options.allowed_tools
            assert "Write" in options.allowed_tools
            # Bash should NOT be in allowed tools
            assert "Bash" not in options.allowed_tools

    def test_uses_model_from_frontmatter_when_available(self, tmp_path: Path):
        """Model from frontmatter takes precedence over provided model."""
        # Arrange
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
model: opus
tools: Read
---
# Test Agent""")

        with patch("src.director.client_factory.ClaudeSDKClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Act: Provide different model than frontmatter
            client, frontmatter = create_subagent_client(
                agent_name="test-agent",
                project_dir=tmp_path,
                model="sonnet"  # Should be overridden by "opus" from frontmatter
            )

            # Assert: Model from frontmatter was used
            options = mock_client_class.call_args[1].get("options") or mock_client_class.call_args[0][0]
            assert options.model == "opus"

    def test_returns_frontmatter_with_client(self, tmp_path: Path):
        """Returns both client and frontmatter dict for caller inspection."""
        # Arrange
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
model: sonnet
tools: Read, Write, Bash
custom_field: custom_value
---
# Test Agent""")

        with patch("src.director.client_factory.ClaudeSDKClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Act
            client, frontmatter = create_subagent_client(
                agent_name="test-agent",
                project_dir=tmp_path,
                model="sonnet"
            )

            # Assert: Frontmatter is returned with parsed values
            assert frontmatter["model"] == "sonnet"
            assert frontmatter["tools"] == "Read, Write, Bash"
            assert frontmatter["custom_field"] == "custom_value"

    def test_raises_when_agent_not_found(self, tmp_path: Path):
        """Raises FileNotFoundError when agent file cannot be found."""
        # Act & Assert: No agent file exists
        with pytest.raises(FileNotFoundError) as exc_info:
            create_subagent_client(
                agent_name="nonexistent-agent",
                project_dir=tmp_path,
                model="sonnet",
                master_dir=tmp_path  # Prevent searching system master dir
            )

        assert "nonexistent-agent" in str(exc_info.value)

    def test_writes_settings_file_to_project_dir(self, tmp_path: Path):
        """Security settings JSON file is written to project directory."""
        # Arrange
        agents_dir = tmp_path / ".claude" / "agents" / "agent-os"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("""---
tools: Read
---
# Test""")

        with patch("src.director.client_factory.ClaudeSDKClient"):
            # Act
            create_subagent_client(
                agent_name="test-agent",
                project_dir=tmp_path,
                model="sonnet"
            )

            # Assert: Settings file was created
            settings_file = tmp_path / ".claude_subagent_settings.json"
            assert settings_file.exists()

            # Verify it's valid JSON with expected structure
            settings = json.loads(settings_file.read_text())
            assert "sandbox" in settings
            assert "permissions" in settings
