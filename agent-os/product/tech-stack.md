# Tech Stack

## Language

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Primary Language | Python 3.x | Existing codebase, strong AI/ML ecosystem, Claude SDK support |
| Type Hints | Yes | Runtime validation optional, improves readability and IDE support |

## AI Integration

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Sub-Agent Spawning | Claude Agent SDK | Official Anthropic SDK for programmatic agent creation |
| Agent Prompts | Markdown files | Human-readable, version-controllable, appendable for improvements |
| Context Management | Per-sub-agent isolation | Each sub-agent gets focused context relevant to its task |
| Agent Configuration | YAML frontmatter | Model, tools, description parsed from agent .md file headers |
| Director Prompt | `prompts/director_prompt.md` | Pre-existing 812-line prompt for orchestration mode |

## Issue Tracking

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Issue Store | Beads | Local-first architecture, no external service dependency |
| CLI Interface | `bd` | Beads CLI for issue creation, updates, queries |
| Graph Intelligence | BV (Beads Viewer) | Dependency visualization, issue relationship mapping, parallel track recommendations |
| Database Location | Single root `.beads/` | One database at harness root; no per-spec databases |

## Parallel Execution

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Concurrent Spawning | `asyncio.TaskGroup` | Python 3.11+ native concurrency, automatic exception propagation |
| Independence Analysis | BV `--robot-plan` | Graph intelligence determines which issues can be worked in parallel |
| Snapshot Mechanism | Git status capture | `snapshot_file_tree()` records HEAD commit and modified files before parallel spawn |
| Merge Strategy | Git merge commands | `git merge {commit} --no-edit` with `git merge --abort` on conflict |
| Conflict Resolution | Priority-based rollback | Higher priority commits kept, lower priority rolled back and reopened |
| Metrics Storage | `.beads/parallel_metrics.json` | JSON file tracking success rates for dynamic scaling decisions |

## Testing

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Test Framework | pytest | Python standard, rich plugin ecosystem |
| Test Harness | Custom automated runner | Gates commits, runs regression suite after each sub-agent change |
| Coverage | pytest-cov | Track test coverage trends |
| Regression Runner | `run_regression_tests()` | npm test with pytest fallback, 5-minute timeout |

## Version Control

| Component | Choice | Rationale |
|-----------|--------|-----------|
| VCS | Git | Industry standard, atomic commits, branch-based isolation |
| Commit Strategy | Atomic per sub-agent | Each completed sub-agent work = one verified commit |
| Conflict Handling | Automatic merge with rollback | Attempt merge, full rollback on failure |
| Git Commands | subprocess module | `subprocess.run()` for `git add -A`, `git commit`, `git merge`, `git merge --abort` |

## Storage

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Local Agent Storage | `.claude/agents/agent-os/` | Per-project, auto-updated on session end |
| Central Agent Storage | `~/agent-os/profiles/default/agents/` | Cross-project, manual rollup (future feature) |
| Improvement Format | Markdown sections | Appendable, human-readable, git-diffable |
| Failure Log | `.beads/improvements.log` | JSON lines format (JSONL), append-only, one entry per line |
| Parallel Metrics | `.beads/parallel_metrics.json` | JSON file for success rate tracking and parallelism scaling |
| Deduplication | MD5 hashing | Standard library `hashlib`, hash learning sections to prevent duplicates |

## Project Structure

```
Linear-Coding-Agent-Harness/
├── .beads/                     # Single Beads database (root-level only)
├── src/
│   ├── director/               # Director orchestration logic
│   │   ├── director.py         # Main Director class and session loop
│   │   ├── spawner.py          # spawn_subagent() implementation
│   │   ├── parallel.py         # Parallel execution infrastructure
│   │   ├── utils.py            # Path utilities, run_command()
│   │   ├── cwd_guard.py        # WorkingDirectoryGuard context manager
│   │   └── improvements.py     # Assess-Improve cycle
│   ├── agents/                 # Sub-agent definitions
│   │   ├── planner.py          # Planning sub-agent
│   │   ├── implementer.py      # Implementation sub-agent
│   │   └── tester.py           # Testing sub-agent
│   └── harness/                # Existing harness code
├── prompts/
│   ├── director_prompt.md      # Director mode prompt (existing)
│   └── sub_agents/             # Sub-agent prompt templates
├── scripts/
│   └── migrate_beads.py        # Migration script for database consolidation
├── specs/
│   └── {spec-name}/            # Individual spec folders
│       ├── spec.md             # Spec definition only
│       └── src/                # Implementation code (flattened)
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── harness/                # Test harness for regression
└── agent-os/
    └── product/                # Product planning documents (mission, roadmap, tech-stack)
```

## Dependencies

### Core
- `anthropic` - Anthropic API client
- `claude-code-sdk` - Claude Agent SDK for sub-agent spawning (matches existing `client.py` patterns)

### Configuration Parsing
- `pyyaml` - YAML frontmatter parsing for agent configuration (model, tools, description)

### Testing
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support

### Utilities
- `pydantic` - Data validation and settings
- `rich` - Terminal output formatting
- `gitpython` - Git operations from Python

### Standard Library (No External Dependencies)
- `hashlib` - MD5 hashing for learning deduplication
- `json` - JSON encoding/decoding for log files and metrics storage
- `pathlib` - Cross-platform path handling
- `datetime` - ISO 8601 timestamps for log entries and metrics records
- `asyncio` - Async execution with `asyncio.timeout()` for sub-agent time limits and `asyncio.TaskGroup` for parallel spawning (Python 3.11+)
- `subprocess` - Execute Beads CLI commands (`bd show --json`), BV commands (`bv --robot-plan`), test runners (`npm test`, `pytest`), and git commands (`git add`, `git commit`, `git merge`, `git status --porcelain`)
- `re` - Regex for YAML frontmatter extraction and SPAWN_SUBAGENT marker parsing (pattern: `r"SPAWN_SUBAGENT:\s*(\S+)\s+(\S+)"`)

## Environment

| Aspect | Specification |
|--------|---------------|
| Python Version | 3.11+ (required for `asyncio.timeout` and `asyncio.TaskGroup`) |
| Package Manager | pip with requirements.txt or poetry |
| Virtual Environment | venv or poetry-managed |
| CI/CD | GitHub Actions (future) |

## Conventions

### Absolute Paths Only (No `cd`)

**All shell commands must use absolute paths. The `cd` command is forbidden.**

Rationale: After `subprocess.run()` with `cwd=` parameter or shell `cd`, agents lose track of their working directory. This causes confusion when subsequent commands assume a different cwd.

Implementation:
- Use `pathlib.Path.resolve()` to convert all paths to absolute before shell execution
- Remove `cwd=` parameter usage from `subprocess.run()` calls
- Construct full absolute paths for all file operations

```python
# CORRECT
project_dir = Path("/home/user/project").resolve()
subprocess.run(["pytest", str(project_dir / "tests")])

# FORBIDDEN
subprocess.run(["pytest", "tests"], cwd="/home/user/project")
subprocess.run("cd /home/user/project && pytest tests", shell=True)
```

### Single Beads Database

**The `.beads/` directory exists only at harness root. No per-spec databases.**

Rationale: Multiple `.beads/` directories cause "2 beads databases detected" warnings and `bd sync` failures.

Implementation:
- Initialize Beads at harness root only
- All `bd` commands run from harness root or use `--project {harness_root}` flag
- Spec folders contain only `spec.md` and implementation code

```
# CORRECT
Linear-Coding-Agent-Harness/
├── .beads/                 # Single database here
└── agent-os/
    └── specs/
        └── my-feature/
            ├── spec.md         # No .beads/ in spec folders
            └── src/

# FORBIDDEN
Linear-Coding-Agent-Harness/
├── .beads/
└── agent-os/
    └── specs/
        └── my-feature/
            ├── .beads/         # NO - causes multi-database errors
            └── spec.md
```

### Folder Structure Conventions

**Product documentation lives in `agent-os/product/`. Spec folders contain only specs and implementation.**

| Content Type | Location |
|--------------|----------|
| Product mission, roadmap, tech-stack | `agent-os/product/` |
| Individual spec definition | `agent-os/specs/{spec-name}/spec.md` |
| Implementation source code | `agent-os/specs/{spec-name}/src/` |
| Tests for a spec | `agent-os/specs/{spec-name}/tests/` |

Agents should NOT look for:
- `planning/` folder in spec directories
- Product docs outside `agent-os/product/`
- Nested `implementation/` folders (flatten to `src/`)

### Working Directory Safety

**Track and validate cwd before multi-command sequences.**

Implementation:
- Log cwd at start of major operations
- Assert cwd matches expected before shell execution
- Use `WorkingDirectoryGuard` context manager for operations that might change cwd
- Fail fast with clear error when unexpected cwd detected

```python
class WorkingDirectoryGuard:
    def __init__(self, expected_cwd: Path):
        self.expected = expected_cwd.resolve()
        self.original = Path.cwd()

    def __enter__(self):
        if Path.cwd() != self.expected:
            raise RuntimeError(f"Unexpected cwd: {Path.cwd()}, expected: {self.expected}")
        return self

    def __exit__(self, *args):
        if Path.cwd() != self.original:
            os.chdir(self.original)
```

---

## Forbidden Patterns

This section explicitly lists patterns that MUST NOT be used in this codebase. These patterns cause agent failures, database conflicts, or unpredictable behavior.

### 1. Working Directory Manipulation

**FORBIDDEN: `cd` command in shell**
```bash
# DO NOT USE
cd /home/user/project
pytest tests

# DO NOT USE
cd /home/user/project && npm test
```

**FORBIDDEN: `cwd=` parameter in subprocess**
```python
# DO NOT USE
subprocess.run(["pytest", "tests"], cwd="/home/user/project")
subprocess.run(["npm", "test"], cwd=project_dir)
```

**FORBIDDEN: `os.chdir()` without guard**
```python
# DO NOT USE (unless wrapped in WorkingDirectoryGuard)
os.chdir("/home/user/project")
run_tests()
```

**WHY:** After these operations, the agent's perception of cwd diverges from reality. Subsequent commands fail silently or operate on wrong directories.

**INSTEAD USE:**
```python
# Absolute paths in command arguments
from src.director.utils import run_command
run_command(["pytest", "tests"], Path("/home/user/project"))

# Or explicit absolute paths
subprocess.run(["pytest", "/home/user/project/tests"])
```

### 2. Relative Paths in Subprocess

**FORBIDDEN: Relative paths without resolution**
```python
# DO NOT USE
subprocess.run(["pytest", "tests"])
subprocess.run(["git", "status"])
subprocess.run(["bd", "list"])
```

**WHY:** These commands assume the current working directory is correct. If cwd has drifted (common in long-running agent sessions), they fail or operate on the wrong location.

**INSTEAD USE:**
```python
# Always use absolute paths
project = Path("/home/user/project").resolve()
subprocess.run(["pytest", str(project / "tests")])
subprocess.run(["git", "-C", str(project), "status"])
subprocess.run(["bd", "--project", str(project), "list"])
```

### 3. Multiple Beads Databases

**FORBIDDEN: `.beads/` in spec directories**
```
# DO NOT CREATE
agent-os/specs/my-feature/.beads/
agent-os/specs/another-feature/.beads/
```

**WHY:** Multiple databases cause:
- "2 beads databases detected" warnings
- `bd sync` failures
- Issue duplication or loss
- Cross-database reference errors

**INSTEAD USE:**
- Single `.beads/` at harness root
- Run `python scripts/migrate_beads.py` to consolidate existing databases

### 4. Nested Implementation Folders

**FORBIDDEN: Deep nesting in spec folders**
```
# DO NOT CREATE
agent-os/specs/my-feature/implementation/src/components/
agent-os/specs/my-feature/planning/docs/
```

**WHY:** Deeply nested structures cause path confusion and make code harder to find.

**INSTEAD USE:**
```
# Flat structure
agent-os/specs/my-feature/
├── spec.md
├── src/
│   └── components/
└── tests/
```

### 5. Shell Commands with `shell=True` and `cd`

**FORBIDDEN: Chained shell commands with directory changes**
```python
# DO NOT USE
subprocess.run("cd /project && npm install && npm test", shell=True)
subprocess.run(f"cd {project_dir} && pytest", shell=True)
```

**WHY:**
- `shell=True` is a security risk
- Directory changes don't persist correctly
- Error handling is poor
- Output capture is unreliable

**INSTEAD USE:**
```python
# Separate commands with absolute paths
project = Path("/home/user/project").resolve()
subprocess.run(["npm", "install"], cwd=None)  # If you must, use git -C style flags
subprocess.run(["pytest", str(project / "tests")])
```

### 6. Hardcoded Paths

**FORBIDDEN: Hardcoded absolute paths in source code**
```python
# DO NOT USE
BEADS_ROOT = Path("/home/jaypaulb/Projects/gh/Linear-Coding-Agent-Harness")
AGENT_PATH = "/home/user/agent-os/profiles/default/agents"
```

**WHY:** Breaks when code runs on different machines or in different locations.

**INSTEAD USE:**
```python
# Derive from file location
BEADS_ROOT = Path(__file__).parent.resolve()

# Or from environment
BEADS_ROOT = Path(os.environ.get("BEADS_ROOT", Path(__file__).parent))
```

### 7. Silent Fallbacks for Path Errors

**FORBIDDEN: Silent fallbacks that hide path problems**
```python
# DO NOT USE
path = get_path() or Path(".")  # Silently uses current directory
config = load_config(path) or {}  # Silently ignores missing config
```

**WHY:** Silent fallbacks hide configuration errors and cause mysterious failures later.

**INSTEAD USE:**
```python
# Fail loudly
path = get_path()
if path is None:
    raise ValueError("Path not configured. Set BEADS_ROOT environment variable.")
config = load_config(path)
if config is None:
    raise FileNotFoundError(f"Config not found at {path}")
```

### 8. Assumptions About Working Directory

**FORBIDDEN: Code that assumes specific cwd**
```python
# DO NOT USE
def run_tests():
    # Assumes we're in project root
    subprocess.run(["pytest", "tests"])
```

**WHY:** cwd is unreliable in agent contexts. It may change between function calls.

**INSTEAD USE:**
```python
def run_tests(project_root: Path):
    # Explicitly requires project root
    test_path = project_root / "tests"
    subprocess.run(["pytest", str(test_path.resolve())])
```

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Standard Library First | Use Python stdlib for core functionality (hashlib, json, pathlib, asyncio, subprocess, re) before adding dependencies |
| Append-Only Logs | Failure log is append-only, no rotation in initial phase |
| Graceful Degradation | Features fail silently when external tools (Beads CLI, BV) unavailable |
| Human-Readable Storage | Markdown for learnings, JSON lines for logs, JSON for metrics - all inspectable without tooling |
| Timeout Safety | Sub-agents have strict 10-minute limit via `asyncio.timeout(600)` to prevent runaway execution |
| Test-Gated Commits | Regression tests must pass before atomic commit workflow completes |
| Priority-Based Resolution | Parallel conflicts resolved by keeping higher priority work, rolling back lower priority |
| Data-Driven Scaling | Parallelism increases/decreases based on measured success rates, not assumptions |
| Absolute Paths Only | All shell commands use absolute paths; `cd` is forbidden to prevent cwd confusion |
| Single Database Root | One `.beads/` at harness root; no per-spec databases to prevent sync conflicts |
| Fail Loudly | Path errors and configuration problems raise exceptions, never silently fall back |
