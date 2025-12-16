# Task Breakdown: Architectural Fixes (Phase 5)

## Overview
Total Tasks: 27 (across 5 task groups)

This is an **infrastructure refactoring spec** - no UI components or API endpoints. Focus is on migration scripts, utility modules, context managers, prompt updates, and documentation.

## Task List

### Atoms Layer

#### Task Group 1: Pure Path Utilities and Validators
**Dependencies:** None
**Suggested Agent:** `atom-writer`
**Rationale:** Pure functions with zero dependencies - path resolution, validation, constants

- [x] 1.0 Complete atoms layer
  - [x] 1.1 Write 3-5 focused atom tests
    - Test `resolve_absolute_path()` with various inputs
    - Test `validate_path_is_absolute()` returns correct boolean
    - Test `get_harness_root()` returns expected path
    - Test `detect_rogue_beads_dirs()` finds spec-level `.beads/`
    - No mocking needed (atoms have no dependencies)
  - [x] 1.2 Add path constants to `beads_config.py`
    - `PRODUCT_DOCS_DIR = HARNESS_ROOT / "agent-os" / "product"`
    - `SPECS_DIR = HARNESS_ROOT / "agent-os" / "specs"`
    - `DIRECTOR_PROMPTS_DIR = HARNESS_ROOT / "prompts"`
    - Follow existing `BEADS_ROOT` pattern
  - [x] 1.3 Create `src/director/utils.py` with pure path atoms
    - `resolve_absolute_path(path: Path | str) -> Path` - resolves and validates
    - `validate_path_is_absolute(path: Path) -> bool` - checks if absolute
    - `get_harness_root() -> Path` - returns resolved harness root
    - `format_command_for_logging(cmd: list) -> str` - formats for debug output
  - [x] 1.4 Create `validate_beads_location()` function in `beads_config.py`
    - Returns `True` if `.beads/` exists only at `BEADS_ROOT`
    - Returns `False` if any spec-level `.beads/` detected
    - Pure function, no side effects
  - [x] 1.5 Create `detect_rogue_beads_dirs()` function in `progress.py`
    - Scans `SPECS_DIR` for any `.beads/` directories
    - Returns `list[Path]` of violating directories
    - Pure scan, no mutations
  - [x] 1.6 Ensure atom tests pass
    - Run ONLY the 3-5 tests written in 1.1
    - All atoms must be pure (no side effects)

**Acceptance Criteria:**
- All atom functions are pure (no side effects)
- Zero dependencies on external modules (only `pathlib`, `os`)
- Path resolution uses `Path.resolve()` consistently
- All tests pass

**Files Created/Modified:**
- `beads_config.py` (modified - add constants, HARNESS_ROOT, validate_beads_location)
- `src/__init__.py` (created)
- `src/director/__init__.py` (created)
- `src/director/utils.py` (created)
- `progress.py` (modified - add detect_rogue_beads_dirs function)
- `tests/__init__.py` (created)
- `tests/test_atoms_path_utilities.py` (created - 25 tests)

---

### Molecules Layer

#### Task Group 2: Composed Helpers - Command Runner and CWD Guard
**Dependencies:** Task Group 1 (atoms)
**Suggested Agent:** `molecule-composer`
**Rationale:** Simple compositions of 2-3 atoms into cohesive helpers for command execution and cwd safety

- [x] 2.0 Complete molecules layer
  - [x] 2.1 Write 4-6 focused molecule tests
    - Test `run_command()` constructs absolute paths correctly
    - Test `run_command()` logs full command for debugging
    - Test `WorkingDirectoryGuard` raises on cwd mismatch
    - Test `WorkingDirectoryGuard` restores cwd on exit
    - Test `validate_cwd()` raises clear error with actual vs expected
    - Minimal mocking (mock subprocess.run only)
  - [x] 2.2 Create `src/director/cwd_guard.py` with `WorkingDirectoryGuard`
    - Constructor takes `expected_cwd: Path`
    - `__enter__`: assert `Path.cwd() == expected_cwd.resolve()`, raise `RuntimeError` if mismatch
    - `__exit__`: restore original cwd if changed during context
    - Log cwd at entry and exit for debugging
    - Uses `resolve_absolute_path()` atom from Task 1.3
  - [x] 2.3 Create `validate_cwd()` function in `src/director/cwd_guard.py`
    - `validate_cwd(expected: Path) -> None`
    - Raises `RuntimeError` with actual vs expected cwd on mismatch
    - Uses `resolve_absolute_path()` atom
    - Standalone function for pre-command validation
  - [x] 2.4 Create `run_command()` helper in `src/director/utils.py`
    - `run_command(cmd: list, project_dir: Path) -> subprocess.CompletedProcess`
    - Constructs absolute paths for all path arguments
    - NO `cwd=` parameter usage
    - Logs full absolute command using `format_command_for_logging()`
    - Uses atoms from Task 1.3
  - [x] 2.5 Ensure molecule tests pass
    - Run ONLY the 4-6 tests written in 2.1
    - Verify cwd guard context manager works correctly

**Acceptance Criteria:**
- Each molecule composes 2-3 atoms
- `WorkingDirectoryGuard` properly saves/restores cwd
- `run_command()` never uses `cwd=` parameter
- Command logging shows full absolute paths
- All tests pass

**Files Created/Modified:**
- `src/director/cwd_guard.py` (created)
- `src/director/utils.py` (modified - add run_command)
- `tests/test_molecules_command_runner.py` (created - 9 tests)

---

### Organisms Layer

#### Task Group 3: Migration Script and Config Integration
**Dependencies:** Task Groups 1 and 2 (atoms and molecules)
**Suggested Agent:** `organism-integrator`
**Rationale:** Complex integration of atoms/molecules for database migration and validation enforcement

- [ ] 3.0 Complete organisms layer
  - [ ] 3.1 Write 4-8 focused organism tests
    - Test migration script exports from spec-level `.beads/`
    - Test migration script imports to root `.beads/`
    - Test migration script deletes spec-level `.beads/` after success
    - Test validation fails if spec-level `.beads/` detected post-migration
    - Test `get_director_prompt()` loads prompt correctly
    - Mock `bd export` and `bd import` subprocess calls
  - [ ] 3.2 Create `scripts/migrate_beads.py` migration script
    - Scan for spec-level `.beads/` using `detect_rogue_beads_dirs()`
    - For each: run `bd export` to extract issues
    - Run `bd import` at root to consolidate
    - Delete spec-level `.beads/` after successful migration
    - Use `run_command()` for all subprocess calls
    - Log all operations for auditability
    - Dry-run mode with `--dry-run` flag
  - [ ] 3.3 Update `progress.py` with validation enforcement
    - Add `assert_single_beads_database()` function
    - Calls `detect_rogue_beads_dirs()` and raises if non-empty
    - Clear error message listing violating directories
    - Called at start of agent sessions
  - [ ] 3.4 Create `get_director_prompt()` in `prompts.py`
    - Follow existing `get_coding_prompt()` pattern
    - Load from `prompts/director_prompt.md`
    - Return prompt string
  - [ ] 3.5 Ensure organism tests pass
    - Run ONLY the 4-8 tests written in 3.1
    - Verify migration script handles edge cases

**Acceptance Criteria:**
- Migration script consolidates all spec-level databases
- Validation fails fast on rogue `.beads/` detection
- Migration is idempotent (safe to run multiple times)
- Dry-run mode shows what would happen without changes
- All tests pass

**Files Created/Modified:**
- `scripts/__init__.py` (created if needed)
- `scripts/migrate_beads.py` (created)
- `progress.py` (modified - add validation)
- `prompts.py` (modified - add director prompt loader)

---

### Prompt & Documentation Layer

#### Task Group 4: Prompt Updates and Documentation
**Dependencies:** Task Group 3 (organisms must exist for prompt to reference)
**Suggested Agent:** `prompt-writer`
**Rationale:** Documentation and prompt updates require understanding of implemented utilities

- [x] 4.0 Complete prompt and documentation updates
  - [x] 4.1 Update `prompts/director_prompt.md` with absolute path section
    - Add "Absolute Path Requirements" section
    - Explicitly forbid `cd` commands
    - Instruct sub-agents to use absolute paths for all file operations
    - Document that `cwd` parameter is forbidden
    - Include example patterns showing correct usage:
      ```
      # CORRECT
      subprocess.run(["pytest", "/absolute/path/to/tests"])

      # FORBIDDEN
      subprocess.run(["pytest", "tests"], cwd="/some/path")
      cd /some/path && pytest tests
      ```
  - [x] 4.2 Add "Forbidden Patterns" section to `agent-os/product/tech-stack.md`
    - List forbidden patterns: `cd`, `cwd=`, relative paths in subprocess
    - Reference the `WorkingDirectoryGuard` context manager
    - Include code examples of what NOT to do
  - [x] 4.3 Update tech-stack.md with single `.beads/` architecture diagram
    - Document consolidated database structure
    - Show directory layout with annotations
    - Reference migration script for legacy cleanup
  - [x] 4.4 Update `.claude/agents/` agent files (if they exist)
    - Add absolute path enforcement instructions
    - Reference harness conventions

**Acceptance Criteria:**
- Director prompt explicitly forbids `cd` commands
- Tech-stack.md has comprehensive "Forbidden Patterns" section
- Architecture diagram clearly shows single database location
- All documentation is consistent with implementation

**Files Modified:**
- `prompts/director_prompt.md`
- `agent-os/product/tech-stack.md`
- `.claude/agents/*.md` (if present)

---

### Integration Layer

#### Task Group 5: Integration Testing and E2E Verification
**Dependencies:** Task Groups 1-4 (all implementation complete)
**Suggested Agent:** `integration-tester`
**Rationale:** Verify all components work together and conventions are enforced

- [ ] 5.0 Complete integration and verification
  - [ ] 5.1 Write 3-5 integration tests
    - Test full migration workflow (create spec `.beads/`, run migration, verify consolidated)
    - Test `WorkingDirectoryGuard` integration with `run_command()`
    - Test validation enforcement catches violations
    - Test path utilities work with real filesystem
    - Test director prompt loads with new sections
  - [ ] 5.2 Run migration script against test fixtures
    - Create temporary spec with `.beads/` directory
    - Run migration in dry-run mode
    - Run migration for real
    - Verify spec-level `.beads/` removed
    - Verify root `.beads/` contains migrated data
  - [ ] 5.3 Verify cwd guard protects against drift
    - Simulate subprocess that changes cwd
    - Verify guard restores original cwd
    - Verify validation catches unexpected cwd
  - [ ] 5.4 Run full test suite for this feature
    - Execute all tests from Task Groups 1-5
    - Expected total: ~18-27 tests
    - All tests must pass
  - [ ] 5.5 Manual verification checklist
    - [ ] Run `python scripts/migrate_beads.py --dry-run` shows expected actions
    - [ ] `beads_config.py` constants resolve to correct paths
    - [ ] `WorkingDirectoryGuard` works in interactive Python session
    - [ ] Director prompt contains absolute path instructions

**Acceptance Criteria:**
- All integration tests pass
- Migration script works end-to-end
- CWD safety mechanisms function correctly
- No spec-level `.beads/` directories remain after migration
- Documentation matches implementation

**Files Created:**
- `tests/test_architectural_fixes.py` (or similar)

---

## Execution Order

Recommended implementation sequence (follows atomic design dependency graph):

| Phase | Task Group | Description | Dependencies |
|-------|------------|-------------|--------------|
| 1 | Task Group 1 | Atoms - Pure path utilities | None |
| 2 | Task Group 2 | Molecules - Command runner, CWD guard | Group 1 |
| 3 | Task Group 3 | Organisms - Migration script, config | Groups 1, 2 |
| 4 | Task Group 4 | Prompts & Documentation | Group 3 |
| 5 | Task Group 5 | Integration Testing | Groups 1-4 |

**Agent Assignment:**
- Task Group 1: `atom-writer` - Specialist in pure functions
- Task Group 2: `molecule-composer` - Specialist in composing atoms
- Task Group 3: `organism-integrator` - Specialist in complex integrations
- Task Group 4: `prompt-writer` - Specialist in documentation and prompts
- Task Group 5: `integration-tester` - Specialist in E2E verification

---

## Existing Code to Leverage

Reference these existing patterns when implementing:

| File | Pattern to Follow |
|------|-------------------|
| `beads_config.py` | `BEADS_ROOT = Path(__file__).parent.resolve()` for path constants |
| `progress.py` | `is_beads_initialized()` pattern for validation functions |
| `prompts.py` | `PROMPTS_DIR` and `load_prompt()` for director prompt loading |
| `tech-stack.md` | `WorkingDirectoryGuard` pseudocode example (lines 216-229) |
| `tech-stack.md` | Absolute path convention examples (lines 139-158) |

---

## Directory Structure After Completion

```
Linear-Coding-Agent-Harness/
├── .beads/                         # Single Beads database (enforced)
├── scripts/
│   └── migrate_beads.py            # NEW: Migration script
├── src/
│   └── director/
│       ├── __init__.py             # NEW: Package init
│       ├── utils.py                # NEW: Path helpers, run_command
│       └── cwd_guard.py            # NEW: WorkingDirectoryGuard
├── tests/
│   └── test_architectural_fixes.py # NEW: Integration tests
├── beads_config.py                 # MODIFIED: Add PRODUCT_DOCS_DIR, SPECS_DIR
├── progress.py                     # MODIFIED: Add rogue detection
├── prompts.py                      # MODIFIED: Add get_director_prompt()
├── prompts/
│   └── director_prompt.md          # MODIFIED: Add absolute path section
└── agent-os/
    └── product/
        └── tech-stack.md           # MODIFIED: Add Forbidden Patterns
```

---

## Test Count Summary

| Task Group | Test Count | Type |
|------------|------------|------|
| Group 1 (Atoms) | 3-5 | Unit tests |
| Group 2 (Molecules) | 4-6 | Unit tests |
| Group 3 (Organisms) | 4-8 | Integration tests |
| Group 4 (Prompts) | 0 | Documentation only |
| Group 5 (Integration) | 3-5 | E2E tests |
| **Total** | **14-24** | Mixed |

---

## Out of Scope Reminders

Per spec, do NOT implement:
- Modifications to Beads CLI itself
- Migration of existing `implementation/src/` code
- Changes to core `agent.py` loop
- Unit tests for WorkingDirectoryGuard (covered by future test spec)
- Windows path compatibility
- Backwards compatibility with pre-Phase-5 structures
