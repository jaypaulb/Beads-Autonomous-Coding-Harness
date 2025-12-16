"""
Sub-Agent Client Factory
========================

Organism for creating restricted Claude SDK clients for sub-agents.
Composes spawn_molecules for agent file loading with security settings
to create clients that respect tool restrictions from agent frontmatter.

This is a complex composition (organism) that:
- Loads agent files with priority cascade
- Extracts tools from frontmatter
- Builds security settings for restricted tool access
- Creates configured ClaudeSDKClient ready for sub-agent use
"""

import json
import os
from pathlib import Path
from typing import Optional

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from claude_code_sdk.types import HookMatcher

from security import bash_security_hook
from .spawn_molecules import load_agent_file


# =============================================================================
# Constants - Default tool and MCP server configurations
# =============================================================================

# Default tools available to sub-agents when not specified in frontmatter
DEFAULT_TOOLS = (
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
)

# File-scoped tools that should be restricted to project directory
FILE_SCOPED_TOOLS = frozenset({
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
})

# Default MCP servers for sub-agents
DEFAULT_MCP_SERVERS = {
    "puppeteer": {"command": "npx", "args": ["puppeteer-mcp-server"]},
}

# Puppeteer MCP tools for browser automation
PUPPETEER_TOOLS = [
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_click",
    "mcp__puppeteer__puppeteer_fill",
    "mcp__puppeteer__puppeteer_select",
    "mcp__puppeteer__puppeteer_hover",
    "mcp__puppeteer__puppeteer_evaluate",
]


# =============================================================================
# Atoms - Pure helper functions
# =============================================================================


def parse_tools_from_frontmatter(frontmatter: dict) -> list[str]:
    """
    Parse the 'tools' field from agent frontmatter into a list.

    This is an atom - pure function with no side effects or dependencies.

    Args:
        frontmatter: Dict parsed from agent file YAML frontmatter

    Returns:
        List of tool name strings. Returns default tools if 'tools' key
        is missing. Returns empty list if tools value is empty string.

    Examples:
        >>> parse_tools_from_frontmatter({"tools": "Read, Write, Bash"})
        ['Read', 'Write', 'Bash']
        >>> parse_tools_from_frontmatter({"model": "sonnet"})  # No tools key
        ['Read', 'Write', 'Edit', 'Glob', 'Grep', 'Bash']
        >>> parse_tools_from_frontmatter({"tools": ""})
        []
    """
    if "tools" not in frontmatter:
        return list(DEFAULT_TOOLS)

    tools_str = frontmatter["tools"]
    if not tools_str or not tools_str.strip():
        return []

    return [tool.strip() for tool in tools_str.split(",") if tool.strip()]


# =============================================================================
# Molecules - Composed helper functions
# =============================================================================


def build_security_settings(
    allowed_tools: list[str],
    project_dir: Path,
    enable_mcp: bool = True
) -> dict:
    """
    Build security settings dict for a sub-agent client.

    This molecule composes tool parsing with permission formatting
    to create the complete security settings structure.

    Args:
        allowed_tools: List of tool names the sub-agent can use
        project_dir: Directory to restrict file operations to
        enable_mcp: Whether to include MCP (puppeteer) tool permissions

    Returns:
        Dict with 'sandbox' and 'permissions' suitable for ClaudeCodeOptions

    Security considerations:
    - File tools (Read, Write, etc.) are restricted to project_dir via glob
    - Bash uses wildcard permission but is validated by security hook
    - MCP tools are optionally included for browser automation
    """
    # Build permission allow list based on provided tools
    allow_list = []

    for tool in allowed_tools:
        if tool in FILE_SCOPED_TOOLS:
            # File-scoped tools restricted to project directory
            allow_list.append(f"{tool}(./**)")
        elif tool == "Bash":
            # Bash uses wildcard - actual validation via security hook
            allow_list.append("Bash(*)")
        else:
            # Unknown tools passed through as-is
            allow_list.append(tool)

    # Include MCP tools if enabled
    if enable_mcp:
        allow_list.extend(PUPPETEER_TOOLS)

    return {
        "sandbox": {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
        },
        "permissions": {
            "defaultMode": "acceptEdits",
            "allow": allow_list,
        },
    }


def write_settings_file(settings: dict, project_dir: Path) -> Path:
    """
    Write security settings to a JSON file in the project directory.

    Args:
        settings: Security settings dict
        project_dir: Directory to write the settings file to

    Returns:
        Path to the written settings file
    """
    # Ensure directory exists
    project_dir.mkdir(parents=True, exist_ok=True)

    settings_file = project_dir / ".claude_subagent_settings.json"
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    return settings_file


# =============================================================================
# Organism - Main factory function
# =============================================================================


def create_subagent_client(
    agent_name: str,
    project_dir: Path,
    model: str,
    master_dir: Optional[Path] = None,
    system_prompt_prefix: Optional[str] = None,
    enable_mcp: bool = True,
    max_turns: int = 1000,
) -> tuple[ClaudeSDKClient, dict]:
    """
    Create a Claude SDK client configured for sub-agent use.

    This organism composes:
    - load_agent_file() to get agent frontmatter and prompt
    - parse_tools_from_frontmatter() to extract allowed tools
    - build_security_settings() to create restricted permissions
    - ClaudeSDKClient with the configured options

    Args:
        agent_name: Name of the agent (e.g., "atom-writer")
        project_dir: Working directory for the sub-agent
        model: Default Claude model to use (overridden by frontmatter)
        master_dir: Optional master directory for fallback agents
        system_prompt_prefix: Optional prefix to add before agent prompt
        enable_mcp: Whether to enable MCP server tools
        max_turns: Maximum turns for the conversation

    Returns:
        Tuple of (ClaudeSDKClient, frontmatter_dict)
        The frontmatter is returned for caller inspection of agent metadata.

    Raises:
        FileNotFoundError: If agent file cannot be found
        ValueError: If CLAUDE_CODE_OAUTH_TOKEN is not set

    Security layers:
    1. Sandbox - OS-level bash command isolation
    2. Permissions - File operations restricted to project_dir
    3. Tool restrictions - Only frontmatter-specified tools allowed
    4. Security hooks - Bash commands validated against allowlist
    """
    # Step 1: Load agent file and extract components
    agent_path, frontmatter, agent_prompt = load_agent_file(
        agent_name=agent_name,
        project_dir=project_dir,
        master_dir=master_dir,
    )

    # Step 2: Determine model (frontmatter takes precedence)
    effective_model = frontmatter.get("model", model)

    # Step 3: Parse allowed tools from frontmatter
    allowed_tools = parse_tools_from_frontmatter(frontmatter)

    # Step 4: Build security settings
    security_settings = build_security_settings(
        allowed_tools=allowed_tools,
        project_dir=project_dir,
        enable_mcp=enable_mcp,
    )

    # Step 5: Write settings to file (required for ClaudeCodeOptions)
    settings_file = write_settings_file(security_settings, project_dir)

    # Step 6: Build system prompt
    if system_prompt_prefix:
        full_prompt = f"{system_prompt_prefix}\n\n{agent_prompt}"
    else:
        full_prompt = agent_prompt

    # Step 7: Get API key
    api_key = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not api_key:
        raise ValueError(
            "CLAUDE_CODE_OAUTH_TOKEN environment variable not set.\n"
            "Run 'claude setup-token' after installing the Claude Code CLI."
        )

    # Step 8: Build MCP servers config
    mcp_servers = DEFAULT_MCP_SERVERS if enable_mcp else {}

    # Step 9: Build hooks (Bash security validation)
    hooks = {}
    if "Bash" in allowed_tools:
        hooks["PreToolUse"] = [
            HookMatcher(matcher="Bash", hooks=[bash_security_hook]),
        ]

    # Step 10: Create the client
    client = ClaudeSDKClient(
        options=ClaudeCodeOptions(
            model=effective_model,
            system_prompt=full_prompt,
            allowed_tools=allowed_tools,
            mcp_servers=mcp_servers,
            hooks=hooks,
            max_turns=max_turns,
            cwd=str(project_dir.resolve()),
            settings=str(settings_file.resolve()),
        )
    )

    return (client, frontmatter)
