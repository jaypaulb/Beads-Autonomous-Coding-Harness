# Linear-to-Beads Conversion Plan

## Overview

Convert the Linear-Integrated Autonomous Coding Agent Harness to use Beads (git-backed local issue tracker) instead of Linear's cloud-based MCP server.

**Key Benefits of Beads:**
- Local-first (no API keys, no network calls)
- Git-backed with JSONL files (automatic version control)
- Designed specifically for AI agents
- Dependency management (blocks, related, parent-child)
- Ready work detection (finds issues with no blockers)
- Hash-based IDs (prevents merge conflicts in multi-agent scenarios)

## Conceptual Mapping

| Linear Concept | Beads Equivalent | Notes |
|----------------|------------------|-------|
| Linear Project | Issue prefix | Set at `bd init` time (e.g., `myproject-1`, `myproject-2`) |
| Team | Not needed | Beads is local-only, no teams |
| Issue | Issue | Direct 1:1 mapping |
| Status: Todo | Status: `open` | Default status |
| Status: In Progress | Status: `in_progress` | Active work |
| Status: Done | Status: `closed` | Completed work |
| Priority 1 (Urgent) | Priority 0 | Beads uses 0=highest |
| Priority 2 (High) | Priority 1 | |
| Priority 3 (Medium) | Priority 2 | |
| Priority 4 (Low) | Priority 3 | |
| Comments | Comments | `bd comment <id> "text"` |
| MCP tools | Bash commands | All `bd` commands support `--json` |
| `.linear_project.json` | `.beads_project.json` | Rename marker file |
| API Key | Not needed | Local database |

## Files to Modify

### 1. **linear_config.py** → **beads_config.py**
**Action:** Rename file and update all configuration constants

**Changes:**
- Rename `LINEAR_API_KEY` → Remove (not needed)
- Rename `LINEAR_PROJECT_MARKER` → `BEADS_PROJECT_MARKER = ".beads_project.json"`
- Update status constants:
  - `STATUS_TODO = "open"` (was "Todo")
  - `STATUS_IN_PROGRESS = "in_progress"` (was "In Progress")
  - `STATUS_DONE = "closed"` (was "Done")
- Update priority mapping:
  - `PRIORITY_URGENT = 0` (was 1)
  - `PRIORITY_HIGH = 1` (was 2)
  - `PRIORITY_MEDIUM = 2` (was 3)
  - `PRIORITY_LOW = 3` (was 4)
- Update issue types:
  - Add `TYPE_FEATURE = "feature"`
  - Add `TYPE_BUG = "bug"`
  - Add `TYPE_TASK = "task"`
- Update META issue title: Keep as `"[META] Project Progress Tracker"`

### 2. **client.py**
**Action:** Remove Linear MCP server, update security to allow Beads CLI commands

**Changes:**
- **Remove:**
  - `LINEAR_TOOLS` array (lines 29-55)
  - `linear_api_key` validation (lines 92-97)
  - Linear MCP server configuration (lines 150-158)
  - Linear references in print statements and system prompt

- **Add:**
  - Beads CLI commands to security allowlist in `ALLOWED_COMMANDS` (via security.py)
  - Update system prompt: `"You are an expert full-stack developer building a production-quality web application. You use Beads (bd) for local issue tracking and work management."`

- **Update:**
  - `allowed_tools` list: Remove `*LINEAR_TOOLS`
  - `mcp_servers`: Remove `"linear"` entry, keep only `"puppeteer"`
  - Print statements: Replace "linear (project management)" with "beads (local issue tracking)"

### 3. **security.py**
**Action:** Add Beads CLI commands to allowlist

**Changes:**
- Add to `ALLOWED_COMMANDS`:
  ```python
  # Beads issue tracker commands
  "bd",  # All bd subcommands are allowed
  ```

**Beads commands that will be used:**
- `bd init` - Initialize tracking
- `bd create` - Create issues
- `bd list` - Query issues
- `bd show` - View issue details
- `bd update` - Update issue status/priority
- `bd close` - Close issues
- `bd comment` - Add comments (alias for `bd comments add`)
- `bd ready` - Find ready work (no blockers)
- `bd dep` - Manage dependencies

### 4. **autonomous_agent_demo.py**
**Action:** Remove Linear API key requirement

**Changes:**
- **Remove:**
  - Lines 90-95: `LINEAR_API_KEY` environment variable check
  - Line 50: Documentation comment about `LINEAR_API_KEY`

- **Keep:**
  - `CLAUDE_CODE_OAUTH_TOKEN` validation (still required)

### 5. **agent.py**
**Action:** Update marker file references

**Changes:**
- Import: `from beads_config import BEADS_PROJECT_MARKER` (was `LINEAR_PROJECT_MARKER`)
- Line 125-126: Update comment and check to use Beads terminology
  ```python
  # We use .beads_project.json as the marker for initialization
  is_first_run = not is_beads_initialized(project_dir)
  ```
- Line 133: Update print message: `"The agent is creating 50 Beads issues and setting up the project"`
- Line 140: Update print message: `"Continuing existing project (Beads initialized)"`

### 6. **progress.py**
**Action:** Update all Linear references to Beads

**Changes:**
- Line 6: Update comment: `"Progress is tracked via Beads issues, with local state cached in .beads_project.json"`
- Line 12: Import: `from beads_config import BEADS_PROJECT_MARKER`
- Rename functions:
  - `load_linear_project_state()` → `load_beads_project_state()`
  - `is_linear_initialized()` → `is_beads_initialized()`
- Line 72: Update print: `"Progress: Beads project not yet initialized"`
- Line 78: Update print: `"Beads Project Status:"`
- Line 81: Update print: `"(Run 'bd info' for current issue counts)"`

### 7. **prompts/initializer_prompt.md**
**Action:** Rewrite to use Beads CLI commands instead of Linear MCP tools

**Major Changes:**
- Remove "Set Up Linear Project" section (lines 15-30)
- Replace with "Initialize Beads" section:
  ```bash
  bd init
  # This creates .beads/ directory and configures git integration
  ```

- Replace "Create Linear Issues" section with Beads equivalent:
  - Instead of `mcp__linear__create_issue`, use:
    ```bash
    bd create "Issue title" -d "Description" -p 0 -t feature --json
    ```

- Update issue creation template:
  - Remove `teamId`, `projectId` (not needed in Beads)
  - Keep: `title`, `description`, `priority`, `type`
  - Add Beads-specific fields: `--labels` for categorization

- Update "Create Meta Issue" section:
  - Use `bd create "[META] Project Progress Tracker" -d "..." -l meta --json`

- Update "Save Linear Project State" section:
  - Rename to "Save Beads Project State"
  - Change filename to `.beads_project.json`
  - Remove `team_id`, `project_id` (not applicable)
  - Add `issue_prefix` field (from `bd info --json`)

- Update verification section:
  - Replace `mcp__linear__list_issues` with `bd list --status open --json`
  - Replace `mcp__linear__update_issue` with `bd update <id> --status in_progress --json`

### 8. **prompts/coding_prompt.md**
**Action:** Rewrite to use Beads CLI commands

**Major Changes:**
- **Step 1 (Get Your Bearings):**
  - Add: `bd info` to see issue tracker status
  - Update line 24: `cat .beads_project.json` (was `.linear_project.json`)

- **Step 2 (Check Beads Status):**
  - Replace `mcp__linear__list_issues` with:
    ```bash
    bd list --status open --json
    bd list --status closed --json
    bd list --status in_progress --json
    ```
  - Replace `mcp__linear__create_comment` with:
    ```bash
    bd comment <issue-id> "Comment text" --json
    ```
  - Remove references to `project_id` and `team_id`

- **Step 4 (Verification Test):**
  - Replace `mcp__linear__list_issues` with `bd list --status closed --limit 2 --json`
  - Replace `mcp__linear__update_issue` with `bd update <id> --status in_progress --json`

- **Step 5 (Select Next Issue):**
  - Replace with: `bd ready --limit 5 --sort priority --json`
  - This uses Beads' built-in "ready work" detection

- **Step 6 (Claim the Issue):**
  - Replace with: `bd update <id> --status in_progress --json`

- **Step 9 (Update Beads Issue):**
  - Replace `mcp__linear__create_comment` with `bd comment <id> "..." --json`
  - Replace `mcp__linear__update_issue` with `bd update <id> --status closed --json`

- **Linear Workflow Rules Section:**
  - Rename to "BEADS WORKFLOW RULES"
  - Update status transitions: `open` → `in_progress` → `closed`

### 9. **README.md**
**Action:** Comprehensive rewrite for Beads integration

**Changes:**
- Title: `# Autonomous Coding Agent Demo (Beads-Integrated)`
- Line 3: Update description to mention Beads instead of Linear
- **Key Features:**
  - Replace "Linear Integration" with "Beads Integration: All work tracked locally in git-backed Beads issues"
  - Replace "Real-time Visibility" with "Git-Backed Progress: All issues versioned in git via JSONL files"
  - Keep "Session Handoff" but update: "Agents communicate via Beads comments"
  - Update "Two-Agent Pattern": "Initializer creates Beads project & issues"

- **Prerequisites:**
  - Remove Linear API key section (lines 39-42)
  - Add Beads installation section:
    ```bash
    # Install Beads
    npm install -g @beads/bd

    # Verify installation
    bd --version
    ```

- **How It Works:**
  - Update diagram (lines 65-88) to show Beads workflow
  - Replace all MCP tool names with `bd` CLI commands

- **Environment Variables Table:**
  - Remove `LINEAR_API_KEY` row
  - Keep only `CLAUDE_CODE_OAUTH_TOKEN`

- **Project Structure:**
  - Line 142: Remove `linear_config.py`, add `beads_config.py`
  - Line 156: Change `.linear_project.json` to `.beads_project.json`

- **MCP Servers Table:**
  - Remove Linear row
  - Keep only Puppeteer

- **Remove "Linear Setup" Section** (lines 179-192)
- **Add "Beads Setup" Section:**
  ```markdown
  ## Beads Setup

  Beads is automatically initialized by the first agent. No manual setup required.

  The initializer agent will:
  - Run `bd init` to create the `.beads/` directory
  - Create 50 issues based on `app_spec.txt`
  - Create a META issue for session tracking

  All issues are stored in `.beads/*.jsonl` files and tracked in git.
  ```

- **Troubleshooting:**
  - Remove LINEAR_API_KEY errors
  - Add Beads-specific troubleshooting:
    ```markdown
    **"bd: command not found"**
    Run `npm install -g @beads/bd` to install Beads CLI.

    **"bd init failed"**
    Ensure git is initialized in the project directory first.
    ```

### 10. **prompts.py** (if exists)
**Action:** Update prompt loading to reference new files

**Changes:**
- Update any file path references from `linear_config.py` to `beads_config.py`
- Update any marker file references from `.linear_project.json` to `.beads_project.json`

## Implementation Strategy

### Phase 1: Configuration & Core Files
1. Rename `linear_config.py` → `beads_config.py` and update constants
2. Update `client.py` to remove Linear MCP, update system prompt
3. Update `security.py` to allow `bd` commands
4. Update `autonomous_agent_demo.py` to remove Linear API key check
5. Update `agent.py` and `progress.py` to use Beads terminology

### Phase 2: Prompts
1. Rewrite `prompts/initializer_prompt.md` with Beads CLI commands
2. Rewrite `prompts/coding_prompt.md` with Beads CLI commands

### Phase 3: Documentation
1. Rewrite `README.md` for Beads integration
2. Update any other documentation files

### Phase 4: Testing
1. Test initializer prompt with a small project
2. Verify issue creation works: `bd list --json`
3. Test coding prompt continuation
4. Verify git integration (JSONL files committed)

## Risk Assessment

### Low Risk
- Beads is more suited for AI agents than Linear (designed for it)
- Local-first means no network failures
- Git-backed provides automatic audit trail
- All `bd` commands support `--json` for programmatic access

### Medium Risk
- Prompts need careful rewriting to use CLI instead of MCP
- Agents need to learn Beads CLI syntax
- No "projects" concept - using issue prefix instead

### Mitigation
- Provide clear examples in prompts
- Use `bd ready` for automatic work discovery
- Use labels to organize issues by category
- Test thoroughly with small project first

## Expected Outcomes

After conversion:
1. **No API keys needed** - Local-only operation
2. **Git-backed issues** - All issues versioned in `.beads/*.jsonl`
3. **Faster operations** - No network latency
4. **Better dependency tracking** - Beads has first-class dependency support
5. **Simpler setup** - No Linear workspace required
6. **Better for multi-agent** - Hash-based IDs prevent conflicts

## Files Summary

**To Rename:**
- `linear_config.py` → `beads_config.py`

**To Modify:**
- `client.py` - Remove Linear MCP, update system prompt
- `security.py` - Add `bd` to allowlist
- `autonomous_agent_demo.py` - Remove API key check
- `agent.py` - Update marker file references
- `progress.py` - Rename functions, update terminology
- `prompts/initializer_prompt.md` - Rewrite for Beads CLI
- `prompts/coding_prompt.md` - Rewrite for Beads CLI
- `README.md` - Comprehensive rewrite

**No Changes:**
- `test_security.py` - Security tests unaffected
- `prompts/app_spec.txt` - Application spec unchanged
- `requirements.txt` - Python dependencies unchanged
