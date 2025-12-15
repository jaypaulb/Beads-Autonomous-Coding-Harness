## YOUR ROLE - INITIALIZER AGENT (Session 1 of Many)

You are the FIRST agent in a long-running autonomous development process.
Your job is to set up the foundation for all future coding agents.

You have access to Beads (`bd`) for local issue tracking. All work tracking
happens in Beads - this is your source of truth for what needs to be built.
Beads is a git-backed issue tracker designed specifically for AI agents.

### FIRST: Read the Project Specification

Start by reading `app_spec.txt` in your working directory. This file contains
the complete specification for what you need to build. Read it carefully
before proceeding.

### SECOND: Initialize Beads

Before creating issues, you need to initialize Beads in the project directory:

```bash
bd init
```

This creates the `.beads/` directory and configures git integration.
Beads will automatically use the directory name as the issue prefix
(e.g., if your directory is "claude-clone", issues will be "claude-clone-abc123").

### CRITICAL TASK: Create Beads Issues

Based on `app_spec.txt`, create Beads issues for each feature using the
`bd create` command. Create 50 detailed issues that comprehensively cover
all features in the spec.

**For each feature, create an issue with:**

```bash
bd create "Issue title" \
  -d "Description with test steps" \
  -p <priority> \
  -t <type> \
  -l <labels> \
  --json
```

**Priority Levels:**
- `0` = Urgent (core infrastructure, database, basic UI layout)
- `1` = High (primary user-facing features, authentication)
- `2` = Medium (secondary features, enhancements)
- `3` = Low (polish, nice-to-haves, edge cases)

**Types:**
- `feature` = New functionality
- `task` = Implementation work
- `bug` = Bug fixes (use for known issues)

**Labels:**
- `functional` - Core functionality features
- `style` - UI/UX polish and styling
- `infrastructure` - Setup, tooling, configuration

**Issue Description Template:**

Each issue description should follow this markdown format:

```markdown
## Feature Description
[Brief description of what this feature does and why it matters]

## Category
[functional OR style]

## Test Steps
1. Navigate to [page/location]
2. [Specific action to perform]
3. [Another action]
4. Verify [expected result]
5. [Additional verification steps as needed]

## Acceptance Criteria
- [ ] [Specific criterion 1]
- [ ] [Specific criterion 2]
- [ ] [Specific criterion 3]
```

**Example Issue Creation:**

```bash
bd create "Auth - User login flow" \
  -d "$(cat <<'EOF'
## Feature Description
Implement secure user authentication with email/password login.

## Category
functional

## Test Steps
1. Navigate to /login page
2. Enter valid email and password
3. Click "Log In" button
4. Verify redirect to dashboard
5. Verify user session persists on refresh

## Acceptance Criteria
- [ ] Login form accepts email and password
- [ ] Invalid credentials show error message
- [ ] Successful login redirects to dashboard
- [ ] Session persists across page refreshes
- [ ] Logout button clears session
EOF
)" \
  -p 1 \
  -t feature \
  -l functional \
  --json
```

**Requirements for Beads Issues:**
- Create 50 issues total covering all features in the spec
- Mix of functional and style features (note category in description)
- Order by priority: foundational features get priority 0-1, polish features get 2-3
- Include detailed test steps in each issue description
- All issues start in "open" status (default)

**CRITICAL INSTRUCTION:**
Once created, issues can ONLY have their status changed (open → in_progress → closed).
Never delete issues, never modify descriptions after creation.
This ensures no functionality is missed across sessions.

### NEXT TASK: Create Meta Issue for Session Tracking

Create a special issue titled "[META] Project Progress Tracker" with:

```bash
bd create "[META] Project Progress Tracker" \
  -d "$(cat <<'EOF'
## Project Overview
[Copy the project name and brief overview from app_spec.txt]

## Session Tracking
This issue is used for session handoff between coding agents.
Each agent should add a comment summarizing their session.

## Key Milestones
- [ ] Project setup complete
- [ ] Core infrastructure working
- [ ] Primary features implemented
- [ ] All features complete
- [ ] Polish and refinement done

## Notes
[Any important context about the project]
EOF
)" \
  -p 0 \
  -t task \
  -l meta \
  --json
```

This META issue will be used by all future agents to:
- Read context from previous sessions (via comments)
- Write session summaries before ending
- Track overall project milestones

**Save the META issue ID from the JSON output** - you'll need it for the project state file.

### NEXT TASK: Create init.sh

Create a script called `init.sh` that future agents can use to quickly
set up and run the development environment. The script should:

1. Install any required dependencies
2. Start any necessary servers or services
3. Print helpful information about how to access the running application

Base the script on the technology stack specified in `app_spec.txt`.

### NEXT TASK: Initialize Git

Create a git repository and make your first commit with:
- init.sh (environment setup script)
- README.md (project overview and setup instructions)
- Any initial project structure files

**Important:** Beads automatically syncs issues to `.beads/*.jsonl` files
which should be committed to git.

Commit message: "Initial setup: project structure and init script"

### NEXT TASK: Create Project Structure

Set up the basic project structure based on what's specified in `app_spec.txt`.
This typically includes directories for frontend, backend, and any other
components mentioned in the spec.

### NEXT TASK: Save Beads Project State

Create a file called `.beads_project.json` with the following information:

```json
{
  "initialized": true,
  "created_at": "[current timestamp]",
  "project_name": "[Name of the project from app_spec.txt]",
  "meta_issue_id": "[ID of the META issue you created, e.g., 'myproject-abc123']",
  "total_issues": 50,
  "issue_prefix": "[The prefix from 'bd info', e.g., 'myproject']",
  "notes": "Project initialized by initializer agent"
}
```

**How to get the issue prefix:**

```bash
bd info --json | grep -o '"prefix":"[^"]*"' | cut -d'"' -f4
```

This file tells future sessions that Beads has been set up.

### NEXT TASK: Validate Dependency Graph

After creating all issues and dependencies, validate the graph structure to ensure
there are no circular dependencies and that priorities align with structural importance.

**CRITICAL:** This validation step prevents deployment-blocking issues like deadlocked
dependency graphs. Do NOT skip this step.

#### 1. Check for Circular Dependencies

Circular dependencies create deadlocks where no work can proceed. Detect them early:

```bash
# Source BV helpers
source /home/jaypaulb/agent-os/profiles/default/workflows/implementation/bv-helpers.md

if bv_available; then
    echo ""
    echo "=== Validating Dependency Graph ==="
    echo ""

    if ! check_cycles; then
        echo ""
        echo "❌ ERROR: Circular dependencies detected!"
        echo ""
        echo "A cycle means Issue A depends on Issue B, which depends on Issue C,"
        echo "which depends back on Issue A. This creates a deadlock where no work"
        echo "can be completed."
        echo ""
        echo "To fix:"
        echo "1. Review the cycle path shown above"
        echo "2. Identify which dependency is incorrect or unnecessary"
        echo "3. Remove it: bd dep remove <child-issue-id> <parent-issue-id> --type blocks"
        echo "4. Re-run this validation"
        echo ""
        echo "DO NOT PROCEED until all cycles are resolved."
        exit 1
    else
        echo "✓ No cycles found - dependency graph is valid"
    fi
fi
```

**Expected output:**
```
=== Validating Dependency Graph ===

✓ No cycles found - dependency graph is valid
```

**If cycles are found:**
- Review the cycle path shown (e.g., "bd-abc → bd-def → bd-ghi → bd-abc")
- Identify the incorrect dependency in the chain
- Remove it: `bd dep remove <issue-id> <blocker-id> --type blocks`
- Re-run check_cycles until validation passes
- **DO NOT CONTINUE** if cycles persist - this indicates a fundamental issue structure problem

#### 2. Run Priority Analysis

BV analyzes the dependency graph to identify priority misalignments - cases where
human-assigned priority doesn't match structural importance:

```bash
if bv_available; then
    echo ""
    echo "=== Analyzing Priority Alignment ==="
    echo ""

    PRIORITY_RECS=$(get_priority_recommendations)

    # Display summary
    echo "$PRIORITY_RECS" | jq -r '
        "Total issues analyzed: \(.summary.total_issues)",
        "Priority recommendations: \(.summary.recommendations)",
        "High confidence (>0.8): \(.summary.high_confidence)",
        ""
    '

    # Show high-confidence misalignments
    HIGH_CONF=$(echo "$PRIORITY_RECS" | jq -r '
        .recommendations[] |
        select(.confidence > 0.8) |
        "  • \(.issue_id): P\(.current_priority) → P\(.suggested_priority) (\(.confidence*100 | round)% confidence)\n    Reason: \(.reasoning)"
    ')

    if [[ -n "$HIGH_CONF" && "$HIGH_CONF" != "" ]]; then
        echo "High-confidence priority adjustments recommended:"
        echo ""
        echo "$HIGH_CONF"
        echo ""

        # Auto-apply high-confidence recommendations
        echo "Applying high-confidence priority updates..."
        echo "$PRIORITY_RECS" | jq -r '
            .recommendations[] |
            select(.confidence > 0.8) |
            "\(.issue_id) \(.suggested_priority)"
        ' | while read -r issue_id new_priority; do
            bd update "$issue_id" --priority "$new_priority" --json > /dev/null
            echo "  ✓ Updated $issue_id to P$new_priority"
        done

        echo ""
        echo "Priority updates complete"
    else
        echo "✓ No high-confidence priority adjustments needed"
    fi
fi
```

**What confidence scores mean:**
- **>0.9**: Very strong signal - graph structure clearly indicates misalignment
- **0.8-0.9**: Strong signal - multiple graph metrics agree
- **0.6-0.8**: Moderate signal - some evidence of misalignment
- **<0.6**: Weak signal - human priorities likely correct

**Common recommendation types:**

*Increase Priority (low priority but high structural importance):*
- **Bottleneck**: Bridges different parts of the graph
- **Critical path**: On the longest dependency chain
- **Wide impact**: Blocks many downstream tasks
- **Foundation**: Connected to other important issues

*Decrease Priority (high priority but low structural importance):*
- **Leaf node**: Few or no dependents
- **Not on critical path**: Can be delayed without cascading effects
- **Isolated**: Completing it doesn't unblock significant work

#### 3. Display Final Graph Summary

Show the overall state of the dependency graph:

```bash
if bv_available; then
    echo ""
    echo "=== Final Graph Summary ==="
    echo ""

    # Get graph insights
    INSIGHTS=$(get_graph_insights)

    # Total issue count
    TOTAL_ISSUES=$(bd list --json | jq '. | length')
    echo "Total issues created: $TOTAL_ISSUES"

    # Ready work count (unblocked issues)
    READY_COUNT=$(bd ready --json | jq '. | length')
    echo "Ready work (unblocked): $READY_COUNT"

    # Show bottlenecks (if any)
    BOTTLENECKS=$(echo "$INSIGHTS" | jq -r '.bottlenecks[:3] | .[] | .id' 2>/dev/null)
    if [[ -n "$BOTTLENECKS" && "$BOTTLENECKS" != "" ]]; then
        echo ""
        echo "Key bottleneck issues (high impact when completed):"
        echo "$BOTTLENECKS" | while read -r issue_id; do
            TITLE=$(bd show "$issue_id" --json | jq -r '.title')
            echo "  • $issue_id: $TITLE"
        done
    fi

    # Show keystones (critical path items)
    KEYSTONES=$(echo "$INSIGHTS" | jq -r '.keystones[:3] | .[] | .id' 2>/dev/null)
    if [[ -n "$KEYSTONES" && "$KEYSTONES" != "" ]]; then
        echo ""
        echo "Critical path issues (must complete for project completion):"
        echo "$KEYSTONES" | while read -r issue_id; do
            TITLE=$(bd show "$issue_id" --json | jq -r '.title')
            echo "  • $issue_id: $TITLE"
        done
    fi

    echo ""
    echo "✓ Dependency graph validation complete"
fi
```

**Important notes:**
- This validation runs AFTER all issue creation is complete
- It's a quality check step that catches structural problems early
- Fails loudly if cycles detected (prevents later deadlocks)
- Auto-applies high-confidence priority recommendations
- Should be the last validation before implementation begins

### OPTIONAL: Start Implementation

If you have time remaining in this session, you may begin implementing
the highest-priority features. Remember:
- Use `bd ready --limit 5 --sort priority --json` to find high-priority open issues
- Use `bd update <issue-id> --status in_progress --json` to claim an issue
- Work on ONE feature at a time
- Test thoroughly before marking status as "closed"
- Add a comment to the issue with implementation notes: `bd comment <issue-id> "..."`
- Commit your progress before session ends

### ENDING THIS SESSION

Before your context fills up:

1. **Commit all work** with descriptive messages (include `.beads/` directory!)

2. **Add a comment to the META issue** summarizing what you accomplished:

```bash
bd comment <meta-issue-id> "$(cat <<'EOF'
## Session 1 Complete - Initialization

### Accomplished
- Created 50 Beads issues from app_spec.txt
- Set up project structure
- Created init.sh
- Initialized git repository
- [Any features started/completed]

### Beads Status
- Total issues: 50
- Closed: X
- In Progress: Y
- Open: Z

### Notes for Next Session
- [Any important context]
- [Recommendations for what to work on next]
EOF
)" --json
```

3. **Ensure `.beads_project.json` exists** and contains all required fields

4. **Leave the environment in a clean, working state**

The next agent will continue from here with a fresh context window.

---

**Remember:** You have unlimited time across many sessions. Focus on
quality over speed. Production-ready is the goal.
