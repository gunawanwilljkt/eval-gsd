<trigger>
Use this workflow when:
- Starting a new session on an existing project
- User says "continue", "what's next", "where were we", "resume"
- Any planning operation when .planning/ already exists
- User returns after time away from project
</trigger>

<purpose>
Instantly restore full project context so "Where were we?" has an immediate, complete answer.
</purpose>

<required_reading>
@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/references/continuation-format.md
@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/references/work-ledger.md
</required_reading>

<resume_source_priority>
**Read the Work Ledger FIRST.** `.planning/LEDGER.md` (Tier-1 HEAD) is the always-warm,
git-verified, sub-task-granular resume source and is the **primary** resumption source when it
exists (`references/work-ledger.md` §3). It **subsumes** the legacy `HANDOFF.json` +
`.continue-here.md` pair.

Source order on resume:
1. **`.planning/LEDGER.md` present** → run the `ledger_resume` step below (the §3
   git-as-ground-truth algorithm). This is authoritative; the legacy artifacts are not consulted
   for the resume position.
2. **No `.planning/LEDGER.md`** → fall through to the **legacy fallback**:
   `HANDOFF.json` → `.continue-here*.md` → PLAN-without-SUMMARY (the `check_incomplete_work`
   path, unchanged). Fully backward-compatible.

This is additive: a project that never adopted the ledger behaves exactly as before.
</resume_source_priority>

<process>

<step name="initialize">
Load all context in one call:

```bash
_GSD_SHIM_NAME="gsd-tools.cjs"; _GSD_RUNTIME_ROOT="${RUNTIME_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"; GSD_TOOLS="${_GSD_RUNTIME_ROOT}/get-shit-done/bin/${_GSD_SHIM_NAME}"; if [ -f "$GSD_TOOLS" ]; then gsd_run() { node "$GSD_TOOLS" "$@"; }; elif [ -f "${_GSD_RUNTIME_ROOT}/.claude/get-shit-done/bin/${_GSD_SHIM_NAME}" ]; then GSD_TOOLS="${_GSD_RUNTIME_ROOT}/.claude/get-shit-done/bin/${_GSD_SHIM_NAME}"; gsd_run() { node "$GSD_TOOLS" "$@"; }; elif command -v gsd-tools >/dev/null 2>&1; then GSD_TOOLS="$(command -v gsd-tools)"; gsd_run() { "$GSD_TOOLS" "$@"; }; elif [ -f "/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/bin/${_GSD_SHIM_NAME}" ]; then GSD_TOOLS="/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/bin/${_GSD_SHIM_NAME}"; gsd_run() { node "$GSD_TOOLS" "$@"; }; else echo "ERROR: gsd-tools.cjs not found at $GSD_TOOLS and gsd-tools is not on PATH. Run: npx -y @opengsd/gsd-core@latest --claude --local" >&2; exit 1; fi
INIT=$(gsd_run query init.resume)
if [[ "$INIT" == @file:* ]]; then INIT=$(cat "${INIT#@file:}"); fi
```

Parse JSON for: `state_exists`, `roadmap_exists`, `project_exists`, `planning_exists`, `has_interrupted_agent`, `interrupted_agent_id`, `commit_docs`.

**If `state_exists` is true:** Proceed to **`ledger_resume` first** (read the ledger HEAD before anything else), then `load_state`.
**If `state_exists` is false but `roadmap_exists` or `project_exists` is true:** Proceed to **`ledger_resume` first** (a ledger can exist even when STATE.md was lost), then offer to reconstruct STATE.md in `load_state`.
**If `planning_exists` is false:** This is a new project - route to /gsd-new-project (no ledger to read; skip `ledger_resume`).

**Resume-source ordering invariant:** when `.planning/LEDGER.md` exists, `ledger_resume` ALWAYS runs before `load_state`/`check_incomplete_work` so the resume position comes from the ledger HEAD first (per `<resume_source_priority>`). STATE.md/PROJECT.md still load afterward for the human-facing status panel only.
</step>

<step name="ledger_resume">
**Primary resume path — runs only when `.planning/LEDGER.md` exists.** This is the proven
git-as-ground-truth algorithm from `references/work-ledger.md §3` (already dogfooded end-to-end —
`design/03-dogfood-proof.md`). When the ledger is absent, SKIP this step entirely and use the
legacy `check_incomplete_work` path below — that keeps pre-ledger projects working unchanged.

```bash
LEDGER=.planning/LEDGER.md
if [ -f "$LEDGER" ]; then echo "LEDGER_PRESENT"; else echo "LEDGER_ABSENT"; fi
```

**If `LEDGER_ABSENT`:** skip to `load_state`, then `check_incomplete_work` (legacy fallback).

**If `LEDGER_PRESENT`, run the algorithm in this exact order.** The order matters:
terminal-state and open-escalation checks MUST short-circuit *before* the forward-progress guard +
generation bump. The §5 guard only trips when `C_now == forward_progress` **and incomplete tasks
remain**, so a *finished* project (no work remaining) would not trip it anyway — but routing
terminal/paused projects out first keeps the guard from even being reached and is the clearer
invariant. (§3 lists escalations at step 3 and terminal at step 5 but runs the guard at step 4;
pulling the terminal check ahead of the guard is the one clarification this wiring makes to §3's
literal order.)

1. **Read Tier-1 HEAD only.** Read `## Next Action`, `## Current Position`, `## Open Escalations`,
   `## Health`, and the frontmatter (`status`, `generation`, `forward_progress`, `position`). Do
   NOT read the Tier-2 `## Task Records` / `## Decision Log` wholesale to orient — that defeats the
   ledger (§9 anti-pattern). Load individual task records on demand only (e.g. to git-verify a
   `done` claim, or to inspect a blocked task's `attempts[]`).

2. **Git-verify before trusting (git is ground truth, the ledger is narrative — §3.2).** For each
   task the ledger marks `done`, confirm its `evidence.commit_sha` is a real commit in this branch's
   history:
   ```bash
   # for each done task's commit_sha (skip 'none'):
   git cat-file -e "${SHA}^{commit}" 2>/dev/null \
     && git merge-base --is-ancestor "$SHA" HEAD 2>/dev/null \
     && echo "$SHA VERIFIED" || echo "$SHA MISSING — demote"
   ```
   - **Missing / not an ancestor of HEAD** → that task is NOT done: demote its record to
     `status: doing`, flag it, and treat its work as not-yet-committed.
   - If the active task carries an `in_progress` marker → **discard any uncommitted half-work** and
     re-run that task **idempotently from `Last clean commit`** (do not resume a half-edit):
     ```bash
     git stash --include-untracked 2>/dev/null || git reset --hard "$LAST_CLEAN_COMMIT"
     ```
   - If that task's `SUMMARY.md` contains `## Self-Check: FAILED` → the task is **not done**
     regardless of what the ledger says. Demote + re-run.

3. **Open Escalations gate (PAUSE branch — §3.3 / §5 rung 2).** If `## Open Escalations` is
   anything other than `None.`/empty, the factory is **PAUSED on a human decision**. Surface the
   escalation block verbatim (it is self-contained: intent at stake, what converged, the diagnosis,
   and the lettered decision options) and **STOP** — do not bump generation, do not run the guard,
   do not start any task. The resume is complete: the human must answer. On their answer, the
   normal flow records the decision in the Decision Log, clears the escalation, and resumes the task
   at the chosen path (§6).

4. **Terminal-state check (CLOSEOUT branch — §3.5).** If `status: complete` (frontmatter) AND the
   HEAD `Next Action` is terminal (all tasks done, no pending implementation task), there is
   **nothing to resume**: do NOT invent new work, do NOT bump generation, do NOT run the guard.
   Route to closeout — `/gsd-verify-work` → `/gsd-extract-learnings` → advance the roadmap — and
   present that as the next action. STOP the resume algorithm here.

5. **Only if real work remains (not paused, not terminal): forward-progress guard, then bump
   generation + snapshot `forward_progress` (§3.4 / §5).** This takeover step is the **sole writer**
   of `generation` and `forward_progress` (W3's per-task execute-phase flush never touches either),
   so there is no double-count. The guard grades the generation that **just finished** by comparing
   its realized output (`C_now`) to its own starting baseline (the inherited `forward_progress`):
   ```
   C_now := completed-task count from git + task records (done tasks whose commit_sha verified)
            # = the just-ended generation's FINAL output

   # --- forward-progress guard (§5, takeover-baseline semantics) ---
   if C_now == frontmatter.forward_progress and incomplete tasks remain:
       # the whole just-ended generation produced ZERO net new completed tasks → do not respawn
       write an Open Escalation (rung 2) naming the stalled task + "no forward progress this
       generation"; set status: blocked; HALT and surface it (same PAUSE as step 3).
   else:
       generation       := generation + 1      # this resume is a new generation taking over
       forward_progress := C_now                # the new generation's STARTING baseline
       # forward_progress is written ONLY here, once per generation; the per-task flush never
       # touches it (§5 single-field invariant).
   ```
   **Why this is correct and terminating (reconciled in W6, finalizing W4's deferred guard):**
   `forward_progress` stores the **starting baseline at takeover**, NOT the previous generation's
   output — that is the fix for the old degeneracy (storing the output made `C_now == forward_progress`
   trivially true at takeover and false-halted every healthy generation). At takeover the just-ended
   generation's *total* output is fully realized, so the comparison is meaningful: equal ⇒ that
   generation added zero tasks. A genuinely stuck gen-1 is caught at the gen-2 takeover
   (`C_now == 0 == forward_progress`), which the old interim `C > 0` stopgap (now removed) masked.
   Every generation either advances `C` strictly (bounded by the task count → terminates at
   completion) or trips the guard (terminates at escalation): provably terminating. The terminal
   (step 4) and escalation (step 3) short-circuits run BEFORE this step, so a finished or paused
   project never reaches the guard.

6. **Continue from `Next Action`.** Present the HEAD's `Next Action` as the resume point and route
   to the matching workflow (execute-phase / plan-phase / etc.) exactly as `determine_next_action`
   does. The ledger HEAD already names the precise next step (task id, red eval rows, last clean
   commit), so the resuming session starts there with no further derivation.

After this step, STATE.md / PROJECT.md still load (next step) for the human-facing status panel,
but the **resume position came from the ledger**, not from STATE.md or the legacy artifacts.
</step>

<step name="load_state">

Read and parse STATE.md, then PROJECT.md:

```bash
cat .planning/STATE.md
cat .planning/PROJECT.md
```

**From STATE.md extract:**

- **Project Reference**: Core value and current focus
- **Current Position**: Phase X of Y, Plan A of B, Status
- **Progress**: Visual progress bar
- **Recent Decisions**: Key decisions affecting current work
- **Pending Todos**: Ideas captured during sessions
- **Blockers/Concerns**: Issues carried forward
- **Session Continuity**: Where we left off, any resume files

**From PROJECT.md extract:**

- **What This Is**: Current accurate description
- **Requirements**: Validated, Active, Out of Scope
- **Key Decisions**: Full decision log with outcomes
- **Constraints**: Hard limits on implementation

</step>

<step name="check_incomplete_work">
**Legacy fallback — only when `.planning/LEDGER.md` was ABSENT** (the `ledger_resume` step ran the
primary path and produced the resume position when the ledger exists). When a ledger is present,
the HANDOFF.json / `.continue-here` artifacts below are NOT the resume source; the ledger is. This
block remains for fully backward-compatible resumption of pre-ledger projects.

Look for incomplete work that needs attention:

```bash
# Check for structured handoff (preferred — machine-readable)
cat .planning/HANDOFF.json 2>/dev/null || true

# Check for continue-here files (phase + non-phase + legacy fallback).
# Use `find` rather than a chained `ls` of bare globs: under zsh's default
# NOMATCH option (macOS default shell), a single non-matching glob aborts
# the entire command during word-expansion — silently dropping every
# pattern after the first miss, including `.planning/.continue-here*.md`.
# `find` does not use shell glob expansion and tolerates absent
# directories on both bash and zsh.
find .planning -maxdepth 3 -name '.continue-here*.md' -print 2>/dev/null || true
find . -maxdepth 1 -name '.continue-here*.md' -print 2>/dev/null || true

# Check for plans without summaries (incomplete execution)
for plan in .planning/phases/*/*-PLAN.md; do
  [ -e "$plan" ] || continue
  summary="${plan/PLAN/SUMMARY}"
  [ ! -f "$summary" ] && echo "Incomplete: $plan"
done 2>/dev/null || true

# Check for interrupted agents (use has_interrupted_agent and interrupted_agent_id from init)
if [ "$has_interrupted_agent" = "true" ]; then
  echo "Interrupted agent: $interrupted_agent_id"
fi
```

**If HANDOFF.json exists (legacy fallback — no ledger present):**

- This is the resumption source **only when no `.planning/LEDGER.md` exists** — structured data from `/gsd-pause-work` (the ledger supersedes it when present)
- Parse `status`, `phase`, `plan`, `task`, `total_tasks`, `next_action`
- Check `blockers` and `human_actions_pending` — surface these immediately
- Check `completed_tasks` for `in_progress` items — these need attention first
- Validate `uncommitted_files` against `git status` — flag divergence
- Use `context_notes` to restore mental model
- Flag: "Found structured handoff — resuming from task {task}/{total_tasks}"
- **After successful resumption, delete HANDOFF.json** (it's a one-shot artifact)

**If .continue-here file exists (phase/non-phase/legacy fallback):**

- This is a mid-plan resumption point
- Read the file for specific resumption context
- Flag: "Found mid-plan checkpoint"

**If PLAN without SUMMARY exists:**

- Execution was started but not completed
- Flag: "Found incomplete plan execution"

**If interrupted agent found:**

- Subagent was spawned but session ended before completion
- Read agent-history.json for task details
- Flag: "Found interrupted agent"
  </step>

<step name="present_status">
Present complete project status to user:

```
╔══════════════════════════════════════════════════════════════╗
║  PROJECT STATUS                                               ║
╠══════════════════════════════════════════════════════════════╣
║  Building: [one-liner from PROJECT.md "What This Is"]         ║
║                                                               ║
║  Phase: [X] of [Y] - [Phase name]                            ║
║  Plan:  [A] of [B] - [Status]                                ║
║  Progress: [██████░░░░] XX%                                  ║
║                                                               ║
║  Last activity: [date] - [what happened]                     ║
╚══════════════════════════════════════════════════════════════╝

[If incomplete work found:]
⚠️  Incomplete work detected:
    - [.continue-here file or incomplete plan]

[If interrupted agent found:]
⚠️  Interrupted agent detected:
    Agent ID: [id]
    Task: [task description from agent-history.json]
    Interrupted: [timestamp]

    Resume with: Task tool (resume parameter with agent ID)

[If pending todos exist:]
📋 [N] pending todos — /gsd-capture --list to review

[If blockers exist:]
⚠️  Carried concerns:
    - [blocker 1]
    - [blocker 2]

[If alignment is not ✓:]
⚠️  Brief alignment: [status] - [assessment]
```

</step>

<step name="determine_next_action">
Based on project state, determine the most logical next action:

**If `.planning/LEDGER.md` exists (primary — the `ledger_resume` step already decided):**
→ If it PAUSED on an Open Escalation → surface the human decision; do not start work.
→ If it routed to closeout (terminal `status: complete`) → offer `/gsd-verify-work` →
  `/gsd-extract-learnings` → advance roadmap.
→ Otherwise → resume from the ledger HEAD `Next Action` (route to its named workflow). The
  HANDOFF.json / `.continue-here` branches below are SKIPPED when a ledger is present.

**If interrupted agent exists (and no ledger):**
→ Primary: Resume interrupted agent (Task tool with resume parameter)
→ Option: Start fresh (abandon agent work)

**If HANDOFF.json exists (legacy fallback — no ledger):**
→ Resume from structured handoff (only when no `.planning/LEDGER.md` exists — the ledger supersedes it)
→ Option: Discard handoff and reassess from files

**If .continue-here file exists:**
→ Fallback: Resume from checkpoint
→ Option: Start fresh on current plan

**If incomplete plan (PLAN without SUMMARY):**
→ Primary: Complete the incomplete plan
→ Option: Abandon and move on

**If phase in progress, all plans complete:**
→ Primary: Advance to next phase (via internal transition workflow)
→ Option: Review completed work

**If phase ready to plan:**
→ Check if CONTEXT.md exists for this phase:

- If CONTEXT.md missing:
  → Primary: Discuss phase vision (how user imagines it working)
  → Secondary: Plan directly (skip context gathering)
- If CONTEXT.md exists:
  → Primary: Plan the phase
  → Option: Review roadmap

**If phase ready to execute:**
→ Primary: Execute next plan
→ Option: Review the plan first
</step>

<step name="offer_options">
Present contextual options based on project state:

```
What would you like to do?

[Primary action based on state - e.g.:]
1. Resume interrupted agent [if interrupted agent found]
   OR
1. Execute phase (/gsd-execute-phase {phase} ${GSD_WS})
   OR
1. Discuss Phase 3 context (/gsd-discuss-phase 3 ${GSD_WS}) [if CONTEXT.md missing]
   OR
1. Plan Phase 3 (/gsd-plan-phase 3 ${GSD_WS}) [if CONTEXT.md exists or discuss option declined]

[Secondary options:]
2. Review current phase status
3. Check pending todos ([N] pending)
4. Review brief alignment
5. Something else
```

**Note:** When offering phase planning, check for CONTEXT.md existence first:

```bash
ls .planning/phases/XX-name/*-CONTEXT.md 2>/dev/null || true
```

If missing, suggest discuss-phase before plan. If exists, offer plan directly.

Wait for user selection.
</step>

<step name="route_to_workflow">
Based on user selection, route to appropriate workflow.

Resume-specific exception: do **not** emit `/clear then:` here. Resume is already a session-entry flow, so the next command should be shown directly.

- **Execute plan** → Show direct next command:
  ```
  ---

  ## ▶ Next Up — [${PROJECT_CODE}] ${PROJECT_TITLE}

  **{phase}-{plan}: [Plan Name]** — [objective from PLAN.md]

  `/gsd-execute-phase {phase} ${GSD_WS}`

  ---
  ```
- **Plan phase** → Show direct next command:
  ```
  ---

  ## ▶ Next Up — [${PROJECT_CODE}] ${PROJECT_TITLE}

  **Phase [N]: [Name]** — [Goal from ROADMAP.md]

  `/gsd-plan-phase [phase-number] ${GSD_WS}`

  ---

  **Also available:**
  - `/gsd-discuss-phase [N] ${GSD_WS}` — gather context first
  - `/gsd-plan-phase --research-phase [N] ${GSD_WS}` — investigate unknowns

  ---
  ```
- **Advance to next phase** → ./transition.md (internal workflow, invoked inline — NOT a user command)
- **Check todos** → Read .planning/todos/pending/, present summary
- **Review alignment** → Read PROJECT.md, compare to current state
- **Something else** → Ask what they need
</step>

<step name="update_session">
Before proceeding to routed workflow, update session continuity:

Update STATE.md:

```markdown
## Session Continuity

Last session: [now]
Stopped at: Session resumed, proceeding to [action]
Resume file: [updated if applicable]
```

This ensures if session ends unexpectedly, next resume knows the state.
</step>

</process>

<reconstruction>
If STATE.md is missing but other artifacts exist:

"STATE.md missing. Reconstructing from artifacts..."

1. Read PROJECT.md → Extract "What This Is" and Core Value
2. Read ROADMAP.md → Determine phases, find current position
3. Scan \*-SUMMARY.md files → Extract decisions, concerns
4. Count pending todos in .planning/todos/pending/
5. Check for .continue-here files → Session continuity

Reconstruct and write STATE.md, then proceed normally.

This handles cases where:

- Project predates STATE.md introduction
- File was accidentally deleted
- Cloning repo without full .planning/ state
  </reconstruction>

<quick_resume>
If user says "continue" or "go":
- Load state silently
- Determine primary action
- Execute immediately without presenting options

"Continuing from [state]... [action]"
</quick_resume>

<success_criteria>
Resume is complete when:

- [ ] If `.planning/LEDGER.md` exists: Tier-1 HEAD read FIRST; every `done` task git-verified (missing commit → demoted); Open Escalations honored (PAUSE if any); terminal `status: complete` routed to closeout WITHOUT tripping the forward-progress guard; otherwise generation bumped + guard run + resumed from `Next Action`
- [ ] If no ledger: legacy HANDOFF.json / `.continue-here` fallback used unchanged
- [ ] STATE.md loaded (or reconstructed)
- [ ] Incomplete work detected and flagged
- [ ] Clear status presented to user
- [ ] Contextual next actions offered
- [ ] User knows exactly where project stands
- [ ] Session continuity updated
      </success_criteria>
