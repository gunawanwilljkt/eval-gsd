# Reference: The Work Ledger Protocol

The Work Ledger (`.planning/LEDGER.md`) is the always-warm, git-verified, sub-task-granular
state that makes **context exhaustion a non-event** and makes an autonomous loop **safe**.
This reference is the operational contract. The file format lives in
@.claude/get-shit-done/templates/ledger.md.

One artifact, three jobs:
- **Handoff** — it is always warm, so a fresh session resumes from it with no special prep.
- **Resume** — it is cross-checked against git, so its claims are trustworthy.
- **Loop-control** — its per-task counters detect non-convergence across context resets.

It subsumes the legacy manual pair `HANDOFF.json` + `.continue-here.md`. STATE.md stays as
the phase-level digest; the ledger is the live task-level state.

---

## 1. The single-writer invariant (non-negotiable)

**Only the orchestrator context writes `LEDGER.md`, in the main working tree.**

Why: execute-phase runs waves in parallel **isolated git worktrees**. Parallel writers →
divergent worktree copies → merge corruption. So the ownership split is:

| Actor | Writes | Returns |
|---|---|---|
| Executor subagent (in worktree) | its own per-plan `SUMMARY.md` only (conflict-free) | a **structured status block** (below) to the orchestrator |
| Orchestrator (main tree) | `LEDGER.md` — merges each returned status sequentially | — |

**Executor return contract** (the executor appends this to its result/SUMMARY so the
orchestrator can merge it deterministically):

```
## LEDGER UPDATE
task: 03-02-T4
status: done | blocked | red
commit_sha: a1b2c3d | none
passing_eval_ids: [EC-12, EC-13]
failing_eval_ids: []
attempt_summary: "implemented handler; ran acceptance_criteria; all green"
self_check: PASSED | FAILED
blocker: none | "<one line>"
```

The orchestrator reads these, **git-verifies** (§3), then writes the ledger. Writes are
serialized by construction — no locks needed.

## 2. Checkpoint discipline (why rot never catches us)

- **Atomic unit = one task = one atomic commit.** The ledger flush rides that boundary.
- **Commit convention (two commits per task):** first the **work commit** (code only — never
  touch the eval/test files in the same commit that turns them green; see §7 gaming check),
  then a separate **ledger flush commit** (`chore(ledger): …`). Keeping them separate keeps
  `git show <work_sha>` clean for the gaming check and makes the ledger history auditable.
- **Never checkpoint mid-edit.** Only at the clean boundary between tasks.
- This **decouples checkpointing (continuous, cheap) from handoff (rare, at a boundary).**
  Because the ledger is never more than one task stale, a handoff needs *no budget to
  compose a handoff* — the resuming session just reads HEAD.
- Therefore the continuation trigger fires at **WARNING (≈35% context remaining), not
  CRITICAL (≈25%)** — you want runway to finish the in-flight task and commit cleanly.

## 3. Git-as-ground-truth resume algorithm

The ledger is narrative; **git is truth.** `/gsd-resume-work` (and any fresh session):

1. Read **Tier-1 HEAD only** (`Next Action`, `Current Position`, `Open Escalations`, `Health`).
2. **Verify** before trusting:
   - For each task the ledger marks `done`: confirm `commit_sha` exists in `git log`. Missing → demote to `doing`, flag.
   - If the active task has an `in_progress` marker: discard any uncommitted half-work; re-run that task **idempotently** from `last_clean_commit`.
   - If a `SUMMARY.md` says `## Self-Check: FAILED`: that task is **not** done regardless of ledger.
3. If `Open Escalations` is non-empty → the factory is **paused**; surface the human question, do not proceed.
4. **Run the forward-progress guard (§5), then bump `generation` +1 and snapshot
   `forward_progress`** — before touching any code. The guard grades the generation that *just
   finished* (compare `C_now` to the inherited `forward_progress`; equal + work remaining → halt +
   rung-2 escalate), then the takeover sets `forward_progress := C_now` as its starting baseline.
   The resume/takeover step is the **sole writer** of `forward_progress` and owns the generation
   bump; the per-task flush never touches either. (**Ordering caveat:** the terminal and
   open-escalation checks below — steps 3 and 5 — MUST short-circuit *before* this guard. A
   *finished* project has `C_now == forward_progress` with **no** work remaining, which the guard
   's "work remaining" clause already excludes; but routing terminal/paused projects out first
   keeps the guard from even being reached and is the clearer invariant.)
5. If the Next Action is a **terminal state** (all tasks done, `status: complete`) there is
   nothing to resume: hand off to closeout (`/gsd-verify-work` → `/gsd-extract-learnings` →
   advance roadmap), do not invent new work — and do not bump generation or run the guard.
6. Otherwise continue from `Next Action`.

## 4. Loop-control — v1 signals (lean: ship 2)

Every signal is derivable from **ledger + git + eval results alone** (no conversation
memory), so a fresh session reconstructs "this task already failed N times" with zero prior
context. v1 ships the two that catch the most thrash; the rest (oscillation, same-file-edit,
budget-burn, wall-clock) are v2 — add only when a real run demands them.

| id | signal | source | default trip |
|---|---|---|---|
| **S1** | consecutive eval-gate failures on the same task | task record `attempts[]` | **3** (mirrors GSD revision cap) |
| **S2** | lifetime attempt cap per task | task record `attempts` length | **5** → abort gate |

A task whose `green_eval_count` is rising never trips S1 (failures must be *consecutive*).

## 5. Escalation ladder — v1 (lean: ship 2 rungs)

The rung is a pure function of ledger counters, so it survives resets (a fresh session does
NOT blindly retry a task already at rung 2).

1. **Rung 1 — retry with a different approach** (while `attempts < S1=3`): re-attempt,
   inlining the failing eval IDs + a one-line "what was tried" into the next attempt. Record
   each attempt.
2. **Rung 2 — escalate to human** (S1 tripped, or S2 cap hit, or a hard blocker): write an
   **Open Escalation** (below), set task `status: blocked`, and **pause the factory**.

> v2 ladder inserts *second-opinion fresh-context subagent* and *re-plan-the-task* between
> these two rungs, plus an anti-storm circuit-breaker. Out of v1 scope by design.

**Forward-progress guard (anti-respawn) — pinned semantics (reconciled in W6).**

The earlier "compare `C == forward_progress` at takeover" formulation was *degenerate*: if
`forward_progress` stored the **previous generation's output** (its count at handoff), then at
takeover `C` already equals it (no work has happened yet since handoff) → the guard would
false-halt *every* fresh generation that inherited progress. The fix is **not** to move the
comparison — at takeover is the only place a *whole* generation's total output is fully realized
and observable — but to fix **what `forward_progress` stores**. It stores the **starting
baseline**, not the output.

- **Definition.** `forward_progress` = the completed-task count `C` **at the moment the current
  generation took over** (its starting baseline). It is written **exactly once per generation, at
  takeover, immediately after the guard check** — it is the *only* place `forward_progress` is
  written. The per-task ledger flush (§1) updates `C`, `Health`, and task records but **never**
  touches `forward_progress`. (Single-writer for this one field = the takeover step.)
- **Guard, at takeover, before overwriting `forward_progress`.** You are grading the generation
  that *just finished* (its full output is now realized):
  1. `C_now` := current completed-task count from git + task records (= the just-ended
     generation's final output).
  2. **If `C_now == forward_progress` AND incomplete tasks remain** → the just-ended generation
     completed **zero** new tasks → **halt + rung-2 escalate** (do not respawn again).
  3. Else proceed, then set `forward_progress := C_now` (the new generation's starting baseline)
     and bump `generation`.
- **Seeding.** The run that *creates* the ledger seeds `generation: 1, forward_progress: 0` and
  does **not** guard (there is no prior generation to grade). Only **takeovers** (resuming an
  existing in-progress ledger) bump generation + run the guard. A genuinely stuck gen-1 is caught
  at the gen-2 takeover: `C_now == 0 == forward_progress` → halt. (This replaces W4's interim
  `C > 0` stopgap, which masked exactly that case.)
- **Why this terminates.** Every generation either completes ≥1 new task (strictly increasing
  `C`, bounded above by the total task count → terminates at completion) or completes 0 (the next
  takeover trips the guard → terminates at escalation). No infinite respawn is possible.

Trace (the dogfood's two-task target): gen-1 created (`fp:0`), runs 0→2, hands off. gen-2
takeover: `C_now=2 == fp=0`? no → proceed, `fp:=2`. gen-2 stalls, `C` stays 2, hands off. gen-3
takeover: `C_now=2 == fp=2`? yes, and a task still remains → **halt + escalate**. A *healthy*
gen-2 (2→3) at the gen-3 takeover reads `C_now=3 ≠ fp=2` → continues. Zero-progress halts, healthy
continues.

## 6. The Open Escalation artifact (async, resumable)

Lives in the ledger HEAD `## Open Escalations`. One stuck task = one block answerable
without re-deriving context:

```
### ESCALATION — task 03-02-T4 (rung 2)
Intent at stake: REQ-07 — "users can resume an interrupted checkout"
Converged / didn't: EC-10,EC-11 green; EC-12,EC-13 red after 3 attempts
Why I'm stuck: [diagnosis — bad eval / impossible task / spec conflict]
Evidence: commits [a1b2c3d, …]; failing eval cmds [...]
THE DECISION I NEED (pick one):
  [a] eval contract wrong — relax EC-12 to {X}
  [b] re-scope task to {Y}
  [c] accept current state and defer
  [d] other
```

On answer: record the decision in the Decision Log, clear the escalation, set the task back
to `doing` at the chosen path, resume.

## 7. Intent-drift detection (passing evals ≠ satisfied intent)

Cross-check, all git/ledger-derivable:
- **Coverage holes:** a `REQ-NN` with no `eval_rows`, or an eval mapping to no REQ → the
  contract can't certify intent. Flag.
- **Eval gaming:** the eval/test file changed in the **same commit** that turned it green
  (`git show <sha> --stat`) → test bent to output, not output fixed to test. Flag, don't pass.
- **Intent audit:** at milestone close, replay the `objective → REQ → eval → commit` trace
  against the objective statement; green-evals-but-unmet-intent → rung-2 escalation naming
  the offending REQ.

## 8. Continuation policy (config knob)

`.planning/config.json` → `continuation.policy`:
- **manual** — ledger stays warm; a human runs `/gsd-resume-work`. (default, most robust)
- **warm-ledger** — same, but the context-monitor hook actively prepares the boundary and
  emits the exact resume command at WARNING.
- **autonomous** — additionally fires a fresh-context spawn (`RemoteTrigger` cloud routine —
  the only primitive that yields a genuinely fresh context) when the tree is clean+pushed.
  Opt-in only; cloud cannot see local uncommitted work.

## 9. Anti-patterns
- ❌ Reading Tier-2 history to orient (defeats the purpose — read HEAD).
- ❌ A subagent writing the ledger (breaks the single-writer invariant).
- ❌ Trusting a ledger `done` without a matching commit (git is truth).
- ❌ Checkpointing mid-edit (only at task=commit boundaries).
- ❌ Retrying a task already at rung 2 (the ledger says stop and ask).
