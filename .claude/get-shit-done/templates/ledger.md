# Work Ledger Template

Template for `.planning/LEDGER.md` — the always-warm, sub-task-granular work ledger.

It is the **read-first source of truth** for *where execution is* and *what to do next*. It
is the keystone artifact behind three capabilities: **handoff** (it is always warm, so a
fresh session resumes from it), **resume** (it is git-verified, so claims are trustable),
and **loop-control** (its per-task counters detect non-convergence across context resets).

It **subsumes** the legacy manual pair `HANDOFF.json` + `.continue-here.md`. STATE.md remains
the phase-level digest; the ledger is the task-level live state.

> **Read the protocol before writing this file:**
> @.claude/get-shit-done/references/work-ledger.md — single-writer invariant, checkpoint
> discipline, git-as-ground-truth cross-check, two-tier read discipline, resume algorithm.

---

## File Template

```markdown
---
ledger_version: '1.0'
status: in-progress            # not-started | in-progress | blocked | complete
generation: 1                  # +1 each fresh-session handoff (respawn guard)
forward_progress: 0            # completed-task count captured at generation takeover = this generation's starting baseline (progress guard; see work-ledger.md §5)
continuation_policy: warm-ledger   # manual | warm-ledger | autonomous
updated: [YYYY-MM-DD HH:MM]
position:
  phase: '[NN-name]'
  plan: '[MM]'
  task: '[T-id]'               # the atomic unit in flight (or last completed)
sole_writer: orchestrator      # INVARIANT: only the orchestrator context writes this file
---

# Work Ledger — read me first

<!-- ===================== TIER 1: HEAD (always read this) ===================== -->
<!-- Keep this section under ~40 lines. A fresh agent reads ONLY this to orient. -->

## Next Action
[ONE concrete next step. A resuming agent starts here. e.g. "Resume task 03-02-T4:
implement POST /sessions handler; eval rows EC-12,EC-13 are red; last clean commit a1b2c3d."]

## Current Position
- Phase: [NN-name] · Plan: [MM] · Task: [T-id]
- Status: [Ready to plan / Executing / Blocked / Phase complete]
- Active task marker: [in_progress: T-id | none]  ·  Last clean commit: [sha | none]

## Open Escalations
[Rung-2 human decisions awaiting an answer — usually empty. Each links a task + the
precise question. Format per `references/work-ledger.md` §Escalation. When non-empty the
factory is PAUSED on these.]

None.

## Health (loop-control at a glance)
- Tasks: [done]/[total] done · [blocked] blocked
- Last 3 task outcomes: [pass, pass, retry×2…]
- Stuck watch: [none | "T-id: 2 consecutive eval-fails (cap 3)"]

<!-- ===================== TIER 2: HISTORY (load on demand) ===================== -->
<!-- Append-only. Git-versioned (committed each task). Do NOT read wholesale to orient. -->

## Task Records

### T-id  [03-02-T4]  — [short title]
- status: doing            # todo | doing | done | blocked
- req_ids: [REQ-07]        # intent traceability (objective → REQ → spec → eval)
- eval_rows: [EC-12, EC-13]   # contract rows this task must turn green
- green_eval_count: 0 / 2
- evidence: { commit_sha: none, passing_eval_ids: [] }
- escalation_rung: 1       # 1 retry · 2 human (v1 ladder; rungs 3-4 = v2)
- attempts:
  - { ts: [...], approach: "first cut of handler", failing_eval_ids: [EC-12,EC-13], commit_sha: none, result: red }
- blocker: none
- human_question_id: none

### T-id  [03-02-T3]  — [short title]
- status: done
- req_ids: [REQ-06]
- eval_rows: [EC-10, EC-11]
- green_eval_count: 2 / 2
- evidence: { commit_sha: a1b2c3d, passing_eval_ids: [EC-10, EC-11] }
- escalation_rung: 1
- attempts:
  - { ts: [...], approach: "...", failing_eval_ids: [], commit_sha: a1b2c3d, result: green }

## Decision Log (append-only)
- [date] [phase]: [decision] — [one-line rationale]
```

<purpose>

The ledger exists to make **context exhaustion a non-event**. Because durable state never
lives only in-context — it is flushed here at every task boundary — a session can be
compacted, ended, or handed off at any moment and a fresh session continues seamlessly.

It replaces the *manual, coarse, one-shot* handoff (HANDOFF.json written only on
`/gsd-pause-work`) with a *continuous, granular, always-warm* artifact. Nothing special has
to happen at handoff time; the ledger is already current.

</purpose>

<two_tier>

**Tier 1 — HEAD** (`Next Action`, `Current Position`, `Open Escalations`, `Health`):
small, always read first. This is the orientation surface. Keep it under ~40 lines so it
costs almost nothing in context.

**Tier 2 — HISTORY** (`Task Records`, `Decision Log`): append-only, git-versioned, loaded
**on demand** (e.g. when loop-control needs a task's attempt history). NEVER read wholesale
to orient — that would reintroduce the context bloat the ledger is meant to fight.

</two_tier>

<single_writer>

**INVARIANT: only the orchestrator context writes `LEDGER.md`, in the main working tree.**

Execute-phase runs waves in parallel, isolated git worktrees. If parallel executors wrote
the ledger, their worktree copies would diverge and corrupt on merge. So:
- Subagents (executors) write **only** their own per-plan `SUMMARY.md` (separate files,
  conflict-free) and **return structured status** to the orchestrator.
- The orchestrator **merges** each returned status into the ledger sequentially as waves
  report, then commits the ledger update.

This makes ledger writes serialized and conflict-free by construction.

</single_writer>

<git_ground_truth>

**Git is ground truth; the ledger is narrative.** On resume, every ledger claim is
cross-checked against `git log` / the working tree before it is trusted:
- A task marked `done` with `commit_sha` that has no matching commit → flagged, not believed.
- A SUMMARY.md with `## Self-Check: FAILED` → the task is not done regardless of ledger.
- The active-task `in_progress` marker + last clean commit → resume re-runs that task
  idempotently from the last clean commit; half-written work is discarded, not resumed.

</git_ground_truth>

<lifecycle>

**Creation:** alongside STATE.md during init (or on first execute-phase if upgrading a
project). Seed HEAD with Phase 1 / "Ready to plan".

**Reading:** FIRST step of every workflow that resumes or executes — read Tier 1 HEAD.
`/gsd-resume-work` reads HEAD, then git-verifies, then continues from `Next Action`.

**Writing (orchestrator only):** at every **task = atomic commit** boundary —
1. update the task's record (status, attempt, evidence, green_eval_count),
2. recompute HEAD (`Next Action`, `Current Position`, `Health`),
3. commit the ledger with the task's commit (or immediately after).
The per-task flush NEVER touches `generation` or `forward_progress`. Those are written once per
generation by the **takeover** (resume) step: it runs the forward-progress guard, then sets
`forward_progress := C` (the completed-task count at takeover = this generation's starting baseline)
and bumps `generation` +1. See `references/work-ledger.md` §5.

</lifecycle>

<size_constraint>

Tier 1 HEAD < ~40 lines (orientation must be cheap). Tier 2 grows append-only but is never
read wholesale. If HEAD drifts large, push detail down into Task Records.

</size_constraint>
