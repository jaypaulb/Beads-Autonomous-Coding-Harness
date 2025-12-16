## YOUR ROLE - INITIALIZER AGENT

You are setting up or updating the Beads issue tracking for a project.
Your job is to ensure all roadmap items have corresponding Beads issues.

You have access to Beads (`bd`) for local issue tracking. All work tracking
happens in Beads - this is your source of truth for what needs to be built.

### STEP 1: Read Product Documentation

Read the product planning documents to understand what needs to be built:

```bash
# Project mission and goals
cat agent-os/product/mission.md

# Roadmap with all work items
cat agent-os/product/roadmap.md

# Technology stack and conventions
cat agent-os/product/tech-stack.md
```

The **roadmap.md** is your primary source. Each numbered item is a work unit.

**IMPORTANT - Understanding Status Markers:**
- `[x] ... **[Spec Complete]**` = Specification is WRITTEN, but code is NOT implemented yet
- `[ ]` = Neither specification nor implementation exists

**ALL items need Beads issues** - both `[x]` and `[ ]` items require implementation work.
The `[x]` just means the technical design is documented in the "Technical Notes" sections.

### STEP 2: Check Existing Beads State

```bash
# Verify Beads connection
bd info
bd stats

# List ALL existing issues
bd list --json

# Check for META issue
bd list --json | jq '.[] | select(.title | contains("[META]"))'
```

**IMPORTANT:** Do NOT create duplicate issues. Compare roadmap items against
existing issues before creating anything new.

### STEP 3: Analyze Gaps

For each roadmap item, check if a corresponding Beads issue exists:
1. Match by title keywords (e.g., "Assess-Improve" matches item 1-3)
2. Match by phase labels
3. Note which items are missing coverage

Create a mental checklist:
- Roadmap Item 1: Issue exists? Y/N
- Roadmap Item 2: Issue exists? Y/N
- ...etc

### STEP 4: Create Missing Issues

**Only create issues for roadmap items that don't have coverage.**

The roadmap is organized into phases. Create issues following this structure:

**Phase Structure (from roadmap.md):**
- Phase 1: Assess-Improve Cycle (Items 1-3)
- Phase 2: Sub-Agent Spawning (Items 4-6)
- Phase 3: Director Mode (Items 7-10)
- Phase 4: Parallel Execution (Items 11-14)
- Phase 5: Architectural Fixes (Items 15-18)

**For each missing item, create an issue:**

```bash
bd create "Phase X: [Item Title from roadmap]" \
  -d "$(cat <<'EOF'
## Roadmap Reference
Item [N] from roadmap.md

## Description
[Copy the item description and bullet points from roadmap.md]

## Technical Notes
[For [x] items: Copy the detailed "Technical Notes (Phase X Spec)" section]
[For [ ] items: Note that implementation details need to be determined]

## File Locations
[Copy the "File Locations" table from technical notes if available]

## Acceptance Criteria
- [ ] Implementation matches roadmap specification
- [ ] Tests pass
- [ ] Code follows tech-stack.md conventions
EOF
)" \
  -p <priority> \
  -t feature \
  -l "phase-X,has-spec" \
  --json
```

**Note:** For `[x]` items, the roadmap contains detailed technical notes including:
- Key decisions made during specification
- Function signatures and class structures
- Integration points with other components
- File locations for implementation

Copy this information into the issue description - it's the implementation blueprint.

**Priority Mapping:**
- Size `S` (Small) = Priority 3
- Size `M` (Medium) = Priority 2
- Size `L` (Large) = Priority 1
- Architectural/Infrastructure = Priority 0

**Labels:**
- `phase-1` through `phase-5` based on roadmap section
- `has-spec` for `[x]` items - detailed technical notes exist in roadmap.md
- `needs-spec` for `[ ]` items - implementation details need to be figured out

### STEP 5: Set Up Dependencies

Issues within a phase often depend on earlier items. Set up dependencies:

```bash
# Item 2 depends on Item 1
bd dep add <item-2-id> <item-1-id>

# Phase 2 items depend on Phase 1 completion
bd dep add <phase-2-first-item> <phase-1-last-item>
```

Use the roadmap notes section for dependency hints:
> "Order follows technical dependencies: learning infrastructure enables improvement,
> sub-agent spawning enables Director mode, sequential execution enables parallel"

### STEP 6: Create or Update META Issue

If no META issue exists, create one:

```bash
bd create "[META] Project Progress Tracker" \
  -d "$(cat <<'EOF'
## Project Overview
Project Development Director - Transform coding harness into orchestrator for sub-agents

## Mission
[Copy key points from mission.md]

## Session Tracking
This issue tracks session handoffs. Each agent adds a comment summarizing their session.

## Phase Status
- [ ] Phase 1: Assess-Improve Cycle (Items 1-3)
- [ ] Phase 2: Sub-Agent Spawning (Items 4-6)
- [ ] Phase 3: Director Mode (Items 7-10)
- [ ] Phase 4: Parallel Execution (Items 11-14)
- [ ] Phase 5: Architectural Fixes (Items 15-18)
EOF
)" \
  -p 0 \
  -t task \
  -l meta \
  --json
```

If META exists, add a comment with current state:

```bash
bd comment <meta-id> "Initializer: Verified issue coverage for roadmap items. [N] issues exist, [M] created this session."
```

### STEP 7: Create Spec-Level Marker

Create `.beads_project.json` in your working directory:

```bash
cat > .beads_project.json << EOF
{
  "initialized": true,
  "created_at": "$(date -Iseconds)",
  "project_name": "Project Development Director",
  "meta_issue_id": "[META issue ID]",
  "total_issues": [count from bd stats],
  "notes": "Issues created from agent-os/product/roadmap.md"
}
EOF
```

**CRITICAL:** The `meta_issue_id` field tells the harness this spec is initialized.

### STEP 8: Validate Dependency Graph

```bash
# Check for cycles (deadlocks)
bv --robot-insights 2>/dev/null | jq '.cycles' || echo "BV not available"

# If cycles found, fix them:
# bd dep remove <child-id> <parent-id>

# View ready issues (no blockers)
bd ready

# View blocked issues
bd blocked
```

### STEP 9: Summary and Handoff

Before ending, output a summary:

```bash
bd stats
bd ready --limit 10
```

Add session comment to META:

```bash
bd comment <meta-id> "$(cat <<'EOF'
## Initializer Session Complete

### Actions Taken
- Read product docs: mission.md, roadmap.md, tech-stack.md
- Checked existing issues: [N] found
- Created new issues: [M] for missing roadmap coverage
- Set up dependencies between phases
- Validated no circular dependencies

### Current State
- Total issues: [from bd stats]
- Ready to work: [count]
- Blocked: [count]

### Recommended Next Steps
- Start with Phase [X] items (highest priority ready work)
- Run `bd ready` to see available work
EOF
)"
```

---

**Key Principles:**
1. **Incremental:** Don't assume fresh start - check what exists first
2. **No duplicates:** Match existing issues before creating new ones
3. **Roadmap-driven:** All issues trace back to roadmap.md items
4. **Dependency-aware:** Set up blockers between phases
5. **Documented:** META issue tracks overall progress
