"""
Spawn Molecules - Composed Helpers for Sub-Agent Spawning
==========================================================

Molecules for loading agent files, fetching issue data from Beads,
and building delegation context for sub-agents. These compose atoms
for YAML parsing, path resolution, and context formatting.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import NamedTuple, Optional


# =============================================================================
# Internal Atoms - Pure functions used by this module
# =============================================================================


class YAMLFrontmatter(NamedTuple):
    """Parsed YAML frontmatter from a markdown file."""
    data: dict[str, str]
    content: str  # Remaining content after frontmatter
    has_frontmatter: bool


# YAML frontmatter pattern: starts with ---, ends with ---
_FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*\n?',
    re.DOTALL
)

# Simple YAML line pattern: key: value (handles basic YAML only)
_YAML_LINE_PATTERN = re.compile(
    r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$'
)


def _extract_yaml_frontmatter(content: str) -> YAMLFrontmatter:
    """
    Extract YAML frontmatter from markdown content.

    Parses the YAML block at the start of a markdown file (between --- markers).
    Supports simple key: value pairs only (no nested structures).

    Args:
        content: Full markdown file content

    Returns:
        YAMLFrontmatter with parsed data dict, remaining content, and success flag
    """
    if not content or not content.strip():
        return YAMLFrontmatter(data={}, content=content or "", has_frontmatter=False)

    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return YAMLFrontmatter(data={}, content=content, has_frontmatter=False)

    yaml_block = match.group(1)
    remaining_content = content[match.end():]

    # Parse simple YAML key: value pairs
    data = {}
    for line in yaml_block.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        line_match = _YAML_LINE_PATTERN.match(line)
        if line_match:
            key = line_match.group(1)
            value = line_match.group(2).strip()
            # Remove surrounding quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            data[key] = value

    return YAMLFrontmatter(
        data=data,
        content=remaining_content,
        has_frontmatter=True
    )


def _resolve_agent_path(
    agent_name: str,
    base_dir: Path | str,
    agents_subdir: str = ".claude/agents/agent-os"
) -> Path:
    """
    Resolve the path to an agent's markdown file.

    Constructs the standard path for agent files following the project convention.
    Does not check if the file exists (pure path resolution only).

    Args:
        agent_name: Name of the agent (e.g., "atom-writer")
        base_dir: Base project directory
        agents_subdir: Subdirectory path for agents

    Returns:
        Resolved Path object to the agent's .md file
    """
    if isinstance(base_dir, str):
        base_dir = Path(base_dir)

    return base_dir / agents_subdir / f"{agent_name}.md"


def _extract_agent_prompt(content: str) -> str:
    """
    Extract the prompt text from agent file content.

    Strips any YAML frontmatter and returns the remaining markdown content.

    Args:
        content: Full agent file content (may include frontmatter)

    Returns:
        The markdown content after frontmatter (prompt text)
    """
    result = _extract_yaml_frontmatter(content)
    return result.content.strip()


# =============================================================================
# Molecules - Composed helpers
# =============================================================================


# Default agent to use when requested agent not found
DEFAULT_AGENT = "implementer"

# Master agent directory (relative to home)
MASTER_AGENTS_PATH = "agent-os/profiles/default/agents"


def load_agent_file(
    agent_name: str,
    project_dir: Path,
    master_dir: Optional[Path] = None
) -> tuple[Path, dict, str]:
    """
    Load an agent file with priority cascade.

    This molecule composes atoms:
    - _resolve_agent_path() for path resolution
    - _extract_yaml_frontmatter() for YAML parsing
    - _extract_agent_prompt() for content extraction

    Search order:
    1. Local: project_dir/.claude/agents/agent-os/{agent_name}.md
    2. Master: ~/agent-os/profiles/default/agents/{agent_name}.md
    3. Fallback: implementer.md at either location

    Args:
        agent_name: Name of the agent (e.g., "atom-writer")
        project_dir: Project directory to search first
        master_dir: Optional master directory (defaults to ~/agent-os)

    Returns:
        Tuple of (path, frontmatter_dict, prompt_text)

    Raises:
        FileNotFoundError: If agent and fallback not found
    """
    if master_dir is None:
        master_dir = Path.home() / "agent-os"

    # Search locations in priority order
    local_path = _resolve_agent_path(agent_name, project_dir)
    master_path = master_dir / "profiles" / "default" / "agents" / f"{agent_name}.md"

    local_fallback = _resolve_agent_path(DEFAULT_AGENT, project_dir)
    master_fallback = master_dir / "profiles" / "default" / "agents" / f"{DEFAULT_AGENT}.md"

    # Try each location in order
    search_paths = [local_path, master_path, local_fallback, master_fallback]

    for path in search_paths:
        if path and path.exists():
            content = path.read_text()
            frontmatter_result = _extract_yaml_frontmatter(content)
            prompt = _extract_agent_prompt(content)

            return (path, frontmatter_result.data, prompt)

    # Nothing found
    raise FileNotFoundError(
        f"Agent '{agent_name}' not found and fallback '{DEFAULT_AGENT}' unavailable. "
        f"Searched: {[str(p) for p in search_paths if p]}"
    )


def load_issue_from_beads(
    issue_id: str,
    project_dir: Path,
    timeout_seconds: int = 30
) -> Optional[dict]:
    """
    Load issue data from Beads using bd CLI.

    Executes `bd show {issue_id} --json` and parses the result.

    Args:
        issue_id: The beads issue ID (e.g., "bd-123")
        project_dir: Project directory with .beads folder
        timeout_seconds: Command timeout

    Returns:
        Dict with issue data or None on failure
    """
    try:
        result = subprocess.run(
            ["bd", "show", issue_id, "--json"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Normalize field names
        return {
            "id": data.get("id", issue_id),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "priority": data.get("priority", 2),
            "assignee": data.get("assignee", ""),
            "status": data.get("status", "open"),
        }

    except subprocess.TimeoutExpired:
        return None
    except json.JSONDecodeError:
        return None
    except FileNotFoundError:
        return None


def build_delegation_context(
    issue: dict,
    agent_prompt: str,
    task_instructions: str
) -> str:
    """
    Build the full delegation context for a sub-agent.

    Combines issue details, agent prompt, and task instructions
    into a formatted markdown string.

    Args:
        issue: Issue dict with id, title, description, tags, priority
        agent_prompt: The agent's base prompt text
        task_instructions: Specific instructions for this task

    Returns:
        Formatted markdown context string
    """
    # Format tags as comma-separated string
    tags = issue.get("tags", [])
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

    context = f"""## Issue Details
- ID: {issue.get('id', 'unknown')}
- Title: {issue.get('title', 'Untitled')}
- Description: {issue.get('description', 'No description')}
- Tags: {tags_str}
- Priority: {issue.get('priority', 'P2')}

{agent_prompt}

## Your Task
{task_instructions}

**Required Steps:**
1. Claim this issue: `bd update {issue.get('id', 'unknown')} --status in_progress`
2. Implement the solution
3. Write tests for your implementation
4. Close the issue: `bd close {issue.get('id', 'unknown')}`
"""

    return context


def verify_issue_closed(
    issue_id: str,
    project_dir: Path,
    timeout_seconds: int = 10
) -> bool:
    """
    Verify an issue has been closed.

    Args:
        issue_id: The beads issue ID
        project_dir: Project directory
        timeout_seconds: Command timeout

    Returns:
        True if issue is closed/done, False otherwise
    """
    issue = load_issue_from_beads(issue_id, project_dir, timeout_seconds)

    if issue is None:
        return False

    status = issue.get("status", "").lower()
    return status in ("done", "closed", "complete", "completed")
