# Autonomous Coding Agent Demo (Beads-Integrated)

A minimal harness demonstrating long-running autonomous coding with the Claude Agent SDK. This demo implements a two-agent pattern (initializer + coding agent) with **Beads as the core project management system** for tracking all work.

## Key Features

- **Beads Integration**: All work tracked locally in git-backed Beads issues
- **Git-Backed Progress**: All issues versioned in git via JSONL files
- **Session Handoff**: Agents communicate via Beads comments, not text files
- **Two-Agent Pattern**: Initializer creates Beads project & issues, coding agents implement them
- **Browser Testing**: Puppeteer MCP for UI verification
- **Claude Opus 4.5**: Uses Claude's most capable model by default

## What is Beads?

[Beads](https://github.com/steveyegge/beads) is a lightweight, git-backed issue tracker designed specifically for AI coding agents. Unlike cloud-based tools like Linear, Beads:

- **Local-first**: No API keys, no network calls, no servers
- **Git-backed**: Issues stored in `.beads/*.jsonl` files and versioned with your code
- **Agent-friendly**: Built-in "ready work" detection finds issues with no blockers
- **Dependency management**: First-class support for task dependencies
- **Merge-safe**: Hash-based IDs prevent conflicts in multi-agent workflows

## Prerequisites

### 1. Install Claude Code CLI and Python SDK

```bash
# Install Claude Code CLI (latest version required)
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Install Beads

```bash
# Install Beads globally via npm
npm install -g @beads/bd

# Verify installation
bd --version
```

### 3. Set Up Authentication

You only need one authentication token (Beads is local-only):

**Claude Code OAuth Token:**
```bash
# Generate the token using Claude Code CLI
claude setup-token

# Set the environment variable
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

### 4. Verify Installation

```bash
claude --version  # Should be latest version
pip show claude-code-sdk  # Check SDK is installed
bd --version  # Check Beads is installed
```

## Quick Start

```bash
python autonomous_agent_demo.py --project-dir ./my_project
```

For testing with limited iterations:
```bash
python autonomous_agent_demo.py --project-dir ./my_project --max-iterations 3
```

## How It Works

### Beads-Centric Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    BEADS-INTEGRATED WORKFLOW                │
├─────────────────────────────────────────────────────────────┤
│  app_spec.txt ──► Initializer Agent ──► Beads Issues (50)  │
│                                              │               │
│                    ┌─────────────────────────▼──────────┐   │
│                    │     .beads/ DIRECTORY              │   │
│                    │  ┌────────────────────────────┐    │   │
│                    │  │ issues.jsonl               │    │   │
│                    │  │ comments.jsonl             │    │   │
│                    │  │ beads.db (local cache)     │    │   │
│                    │  └────────────────────────────┘    │   │
│                    │  Git-tracked, versioned with code  │   │
│                    └────────────────────────────────────┘   │
│                                              │               │
│                    Coding Agent queries Beads               │
│                    ├── bd ready (find ready work)           │
│                    ├── bd update (claim issue)              │
│                    ├── Implement & test with Puppeteer      │
│                    ├── bd comment (add notes)               │
│                    └── bd update --status closed            │
└─────────────────────────────────────────────────────────────┘
```

### Two-Agent Pattern

1. **Initializer Agent (Session 1):**
   - Reads `app_spec.txt`
   - Runs `bd init` to initialize Beads
   - Creates 50 Beads issues with detailed test steps
   - Creates a META issue for session tracking
   - Sets up project structure, `init.sh`, and git

2. **Coding Agent (Sessions 2+):**
   - Runs `bd ready` to find highest-priority issue with no blockers
   - Runs verification tests on previously completed features
   - Claims issue with `bd update <id> --status in_progress`
   - Implements the feature
   - Tests via Puppeteer browser automation
   - Adds implementation comment with `bd comment <id> "..."`
   - Marks complete with `bd update <id> --status closed`
   - Updates META issue with session summary

### Session Handoff via Beads

Instead of local text files, agents communicate through:
- **Issue Comments**: Implementation details, blockers, context (via `bd comment`)
- **META Issue**: Session summaries and handoff notes
- **Issue Status**: `open` / `in_progress` / `closed` workflow
- **Git History**: All issue state changes committed with code

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth token (from `claude setup-token`) | Yes |

Note: No API keys needed for Beads - it's local-only!

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | `./autonomous_demo_project` |
| `--max-iterations` | Max agent iterations | Unlimited |
| `--model` | Claude model to use | `claude-opus-4-5-20251101` |

## Project Structure

```
beads-agent-harness/
├── autonomous_agent_demo.py  # Main entry point
├── agent.py                  # Agent session logic
├── client.py                 # Claude SDK + MCP client configuration
├── security.py               # Bash command allowlist and validation
├── progress.py               # Progress tracking utilities
├── prompts.py                # Prompt loading utilities
├── beads_config.py           # Beads configuration constants
├── prompts/
│   ├── app_spec.txt          # Application specification
│   ├── initializer_prompt.md # First session prompt (creates Beads issues)
│   └── coding_prompt.md      # Continuation session prompt (works issues)
├── requirements.txt          # Python dependencies
└── CONVERSION_PLAN.md        # Plan for Linear→Beads conversion
```

## Generated Project Structure

After running, your project directory will contain:

```
my_project/
├── .beads/                   # Beads issue tracker directory
│   ├── beads.db              # Local SQLite cache for fast queries
│   ├── issues.jsonl          # Git-tracked issue data
│   ├── comments.jsonl        # Git-tracked comments
│   └── config.json           # Beads configuration
├── .beads_project.json       # Project state (marker file)
├── app_spec.txt              # Copied specification
├── init.sh                   # Environment setup script
├── .claude_settings.json     # Security settings
└── [application files]       # Generated application code
```

## MCP Servers Used

| Server | Transport | Purpose |
|--------|-----------|---------|
| **Puppeteer** | stdio | Browser automation for UI testing |

Note: Beads uses CLI commands (`bd`), not MCP.

## Security Model

This demo uses defense-in-depth security (see `security.py` and `client.py`):

1. **OS-level Sandbox:** Bash commands run in an isolated environment
2. **Filesystem Restrictions:** File operations restricted to project directory
3. **Bash Allowlist:** Only specific commands permitted (npm, node, git, bd, etc.)
4. **MCP Permissions:** Tools explicitly allowed in security settings

## Beads Setup

Beads is automatically initialized by the first agent. No manual setup required.

The initializer agent will:
- Run `bd init` to create the `.beads/` directory
- Create 50 issues based on `app_spec.txt`
- Create a META issue for session tracking

All issues are stored in `.beads/*.jsonl` files and tracked in git.
Each `git commit` includes the current state of all issues, providing a complete
audit trail of what was implemented when.

## Viewing Progress

You can check progress at any time:

```bash
# View all issues
bd list

# View issue details
bd show <issue-id>

# Count progress
bd list --status closed --json | jq 'length'  # Completed
bd list --status open --json | jq 'length'    # Remaining

# Find ready work (high priority, no blockers)
bd ready --limit 10 --sort priority

# View dependency tree
bd dep tree <issue-id>

# View comments on an issue
bd comments list <issue-id>
```

## Customization

### Changing the Application

Edit `prompts/app_spec.txt` to specify a different application to build.

### Adjusting Issue Count

Edit `prompts/initializer_prompt.md` and change "50 issues" to your desired count.

### Modifying Allowed Commands

Edit `security.py` to add or remove commands from `ALLOWED_COMMANDS`.

## Troubleshooting

**"CLAUDE_CODE_OAUTH_TOKEN not set"**
Run `claude setup-token` to generate a token, then export it.

**"bd: command not found"**
Run `npm install -g @beads/bd` to install Beads CLI.

**"bd init failed"**
Ensure git is initialized in the project directory first. Beads requires git.

**"Appears to hang on first run"**
Normal behavior. The initializer is creating 50 Beads issues with detailed descriptions. Watch for `[Tool: Bash]` output showing `bd create` commands.

**"Command blocked by security hook"**
The agent tried to run a disallowed command. Add it to `ALLOWED_COMMANDS` in `security.py` if needed.

## Beads CLI Reference

Here are the most commonly used Beads commands:

```bash
# Initialize Beads in a project
bd init

# Create an issue
bd create "Issue title" -d "Description" -p 0 -t feature --json

# List issues
bd list --status open --json
bd list --status closed --limit 10 --json

# Show issue details
bd show <issue-id>

# Update issue status
bd update <issue-id> --status in_progress --json
bd update <issue-id> --status closed --json

# Add a comment
bd comment <issue-id> "Comment text" --json

# View comments
bd comments list <issue-id>

# Find ready work (no blockers)
bd ready --limit 5 --sort priority --json

# Manage dependencies
bd dep add <dependent-id> <blocker-id> --type blocks
bd dep tree <issue-id>

# Get project info
bd info --json
```

All commands support `--json` for programmatic access.

## Why Beads Instead of Linear?

1. **No API Keys**: Local-only, no network calls, no authentication
2. **Git Integration**: Issues versioned alongside code automatically
3. **Offline Work**: No internet required, no rate limits
4. **Faster**: Local database, <100ms queries
5. **Agent-Designed**: Built specifically for AI coding agents
6. **Better Dependencies**: First-class dependency management with `bd dep`
7. **Automatic Ready Work**: `bd ready` finds issues with no blockers
8. **Merge-Safe**: Hash-based IDs prevent conflicts in multi-agent scenarios

## License

MIT License - see [LICENSE](LICENSE) for details.
