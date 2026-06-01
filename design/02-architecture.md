# 02 — Architecture: Eval-First, Context-Resilient GSD

> How this doc was produced (so you can trust it): advisor pass #1 reshaped the thesis;
> then 3 parallel peer agents explored *variants* of the hard parts (continuation,
> loop-control, eval unification), each grounded in the real GSD source. This doc records
> the **variants considered** (transparency — "all things considered") and the **locked
> decision** for each, then assembles them into one architecture. Factual claims here come
> from close reading of the actual workflow/agent files and override looser earlier notes.

---

## 0. The central realization

The four "pillars" collapse into something simpler and more buildable:

- **Pillars B (handoff), C (ledger), D (loop-control) are unified by ONE artifact: the
  Work Ledger.** Handoff works because the ledger is always warm. Loop-control works
  because the ledger carries attempt counters. Resume works because the ledger is
  read-first and git-verified. → Build the ledger well and three pillars fall out of it.
- **Pillar A (eval-first) is ~90% WIRING, not building.** GSD's executor (`execute-plan`)
  **already hard-gates every task** on `<acceptance_criteria>` ("BLOCKED from starting the
  next task until this gate clears"). `verify-phase` **already blocks** on test failure.
  The real defect: **AI-SPEC §5–7 (the eval strategy) is *orphaned*** — neither
  `gsd-planner` nor `gsd-executor` ever reads it; only the retroactive `gsd-eval-auditor`
  does. So intent is written and never wired to the gate that already exists.

**Net:** one new durable substrate (the ledger) + connecting wires that already terminate
one end short + a few small new guards. This is an evolution measured in edits, not a rewrite.

### Factual corrections that shaped the design (from close code reading)
| Earlier loose claim | Reality (verified) |
|---|---|
| VALIDATION.md is authored post-execution | Authored at **plan-phase** (Step 6) from template; post-hoc only on the `validate-phase` *reconstruction* path |
| Execute test-gating is only a soft warning | **Per-task `<acceptance_criteria>` is a HARD gate** today; only the **post-wave integration** suite is a soft "Fix now / Continue" warning |
| verify-phase is advisory | verify-phase **blocks**: "a phase cannot be verified if tests fail" |
| Evals aren't gating because nothing runs | The gate *runs*; the **eval *intent* (AI-SPEC §5–7) is orphaned** from planner/executor |

---

## 1. Pillar A — Eval-first (unify the contract, keep evaluators plural)

**Variants considered**
- **A-i. Invent a new "eval contract" concept + new runner.** ✗ Rejected — duplicates the
  existing acceptance-criteria gate; risks the "beautiful framework never run" failure.
- **A-ii. Unify all 4 verification artifacts into ONE verdict-producer.** ✗ Rejected —
  collapsing destroys GSD's deliberate *generation ≠ evaluation* separation, loses
  human-UAT's irreplaceable lens, and can't host LLM-judge calibration.
- **A-iii. Unify the CONTRACT (one authored artifact, spec-time, locked, gating); keep the
  EVALUATORS plural (deterministic gate / independent judge / human UAT).** ✓ **CHOSEN.**

**Locked decisions**
- **A1.** One **Eval Contract** per phase = the single authored artifact (evolve the
  existing `VALIDATION.md`; absorb `AI-SPEC §5` eval rows into it). Evaluators stay plural.
- **A2. De-orphan AI-SPEC §5–7.** `gsd-planner` reads the eval contract and emits its
  deterministic rows as `<acceptance_criteria>` on the relevant tasks → the executor's
  *existing* hard gate enforces them for free. This is the single highest-leverage wire.
- **A3.** The contract is **authored at spec time, mandatory for every phase** (not just AI
  phases), and **locked** (a `locked_hash` in frontmatter).
- **A4. Contract row fields:** `id`, `objective_ref`, `req_ref`, `behavior` (the acceptance
  statement), `measurement` (`Code | Judge | Human`), `command_or_rubric`, `sample_rate`
  (`per-task | per-wave | pre-verify`), `severity` (`gate | warn`), `locked_hash`.
- **A5. Altitude = behavioral acceptance, NOT unit.** Writable before code exists:
  "POST /x with body B → 201 + schema S", "migration applies on clean DB", "route /dash
  renders without error". Forbidden: "`foo()` returns `bar`" (couples to unchosen impl).
- **A6. Independence mechanism = lock-before-code + diff-detect weakening.** The real risk
  isn't "same AI writes code+evals," it's "evals weakened *after seeing how hard the code
  is.*" So: freeze + hash the contract at plan time; `verify-phase` flags any commit that
  deletes/skips/weakens a locked eval (reuse the existing `audit_test_quality`). Reserve an
  **independent judge agent** only for subjective/Judge-measurement rows.
- **A7. Bidirectional traceability + coverage gate.** Every eval carries
  `objective_ref → req_ref` (forward). A **coverage gate** flags every objective/REQ with
  zero evals and every eval mapping to nothing (backward). Eval↔objective bijection is how
  spec-drift-from-intent surfaces.
- **A8. Measurement split (keeps it cheap & mandatory-able):** deterministic for
  structure/contract (the ~80%), calibrated **judge** only for subjective quality
  ("is the error message *clear*"), **human-UAT** for experience & high-stakes. Never
  mandate a judge on plain CRUD — that's where velocity dies.

**Why this is "evals alongside, not separate":** the contract is authored *with* the spec,
its deterministic rows ride the *per-task* gate that already fires on every task, and its
`sample_rate` drives per-wave / pre-verify cadence. Red→green on contract rows literally
*is* task progress.

---

## 2. Pillar C — The Work Ledger (the spine that unifies B, C, D)

**Variants considered**
- **C-i.** Keep STATE.md + manual HANDOFF.json separate (status quo). ✗ coarse, manual,
  not sub-task granular.
- **C-ii.** Add a third new ledger file beside them. ✗ sprawl; three sources of truth.
- **C-iii.** **One always-warm ledger that subsumes STATE.md + HANDOFF.json**, sub-task
  granular, git-verified. ✓ **CHOSEN.**

**Locked decisions**
- **C1.** The ledger is **continuously updated, sub-task granular, read-first**, machine +
  human readable (markdown + frontmatter). It is *the* handoff and *the* loop-control state.
- **C2. Git is ground truth; the ledger is narrative.** On resume, **every ledger claim is
  cross-checked against `git log` / working tree**; a "done" task with no matching commit is
  flagged, not believed. (Defends against poisoned/stale ledgers and generator self-report.)
- **C3. Per-task ledger record:** `status` (`todo|doing|done|blocked`), `attempts[]`
  (`{ts, approach, failing_eval_ids, commit_sha|none, result}`), `green_eval_count`,
  `eval_history` (per eval id, for oscillation), `escalation_rung` (1–4), `req_ids[]`,
  `evidence` (`{commit_sha, passing_eval_ids}`), `blocker`, `next_action`,
  `human_question_id`. Frontmatter adds a `generation` counter (respawn guard) and
  `forward_progress` marker (completed-task count at last spawn).

This single record simultaneously powers: resume (C), handoff warmth (B), and
non-convergence detection (D). That is the architecture's keystone.

---

## 3. Pillar B — Context-resilient continuation

**Platform facts (verified):** only **`RemoteTrigger`** (claude.ai cloud routine) yields a
genuinely *fresh* context. `ScheduleWakeup` / `CronCreate` / `/loop` re-fire into the
*same*, already-degrading session. The harness **also auto-compacts in-session**, so a
single session survives longer than naive assumption — but compaction may drop detail.

**Variants considered**
- **B-A.** Always-warm ledger + one-command local `/gsd-resume` (sees working tree).
- **B-B.** Lean orchestrator: heavy work to fresh subagents; orchestrator self-checkpoints
  at task boundaries (subagent exhaustion is bounded to one task & self-heals).
- **B-C.** Fully autonomous: monitor hook fires `RemoteTrigger` to spawn fresh cloud
  session (requires committed+pushed state; blind to local uncommitted work).

**Locked decision: B-A + B-B as the robust default core; B-C as an opt-in layer.**
- **B1. The ledger IS the handoff** — there is no separate handoff artifact to compose, so
  the trigger needs no budget to "write a handoff," it just wraps to a boundary.
- **B2. Checkpoint discipline:** atomic unit = **one task = one atomic commit**; the ledger
  flush rides that commit. **Never checkpoint mid-edit.** Fire the continuation trigger at
  **WARNING (35% remaining), not CRITICAL (25%)** — you need runway to hand off cleanly.
  This *decouples* checkpointing (continuous, free) from handoff (rare, at a boundary), so
  "context rot" never catches us holding irreplaceable in-context state.
- **B3. Continuation policy knob** in `.planning/config.json`:
  `continuation.policy: manual | warm-ledger | autonomous`. `autonomous` is the only mode
  that fires `RemoteTrigger`, and only when the tree is clean+pushed.
- **B4. Hook upgrade:** `gsd-context-monitor.js` evolves from *advise* → *orchestrate*. Its
  current "do NOT write handoff files" advice becomes correct for a **new reason** (ledger
  is already warm). At WARNING: "flush ledger, wrap to task boundary, prepare resume." At
  CRITICAL: emit the resume command, or fire `RemoteTrigger` if policy=autonomous.
- **B5. Resume safety:** generation counter + **forward-progress guard** (only continue if
  completed-task count increased since last spawn) → no infinite respawn. `in_progress`
  marker + idempotent re-run from last clean commit → mid-edit interruptions discard
  half-work, never resume it.

---

## 4. Pillar D — Loop-control / stuck-detection / escalation (makes autonomy SAFE)

Every signal is derivable from **ledger + git + eval results alone** — a fresh session
reconstructs "this task failed 3× already" with zero prior memory. This is the one thing
GSD's gates lack today: **durable, per-task, cross-session counting that auto-escalates.**

**Locked decisions**
- **D1. Non-convergence signals (defaults rhyme with existing GSD constants — revision cap
  3, stall 5/10 min, context POOR=70%):**
  - S1 ≥3 consecutive eval-gate failures on a task · S2 green-eval count flat over 2
    attempts · S3 ≥3 edits to same file, 0 net-new green · S4 ≥2 eval pass↔fail flips ·
    S5 ≥3 tasks closed with no net-new green · S6 POOR(70%) + 0 new green → checkpoint/abort
    · S7 ≥10 min no commit · S8 lifetime cap 5 attempts/task → abort gate.
- **D2. Escalation ladder** (maps onto existing `gates.md` Pre-flight/Revision/Escalation/
  Abort taxonomy; rung is a pure function of ledger counters so it survives resets):
  1) retry w/ different approach (Revision, attempts<3) → 2) **second-opinion** fresh-context
  `gsd-verifier`/`gsd-plan-checker` to diagnose *why* (catches "the eval is wrong") →
  3) re-plan the task (`/gsd-plan-phase {N} --gaps`, existing 1-retry cap) → 4) **human
  escalation**.
- **D3. Intent-drift detection:** coverage holes (REQ↔eval bijection, §A7) + **eval-gaming
  detection** (the eval/test file changed in the *same commit* that turned it green = test
  bent to output → flag, don't pass; git-derivable) + intent audit (`gsd-audit-milestone`
  consumes the REQ→eval→commit trace vs the objective statement).
- **D4. Human-escalation artifact:** extend `.continue-here.md` with an `## ESCALATION`
  block — *intent at stake (REQ-NN + objective one-liner)*, converged/didn't, *why stuck*
  (rung-2 diagnosis), evidence (commits/flips), and **"THE DECISION I NEED"** with options
  that map 1:1 to the `multi-option-escalation` gate. Answerable async; on answer the factory
  records the decision in the ledger and resumes at the chosen rung.
- **D5. Anti-storm:** dedupe escalations by root cause (group those sharing a failing
  REQ-NN/file into one), rate-limit to one open human block per phase, circuit-breaker
  pauses the factory at 3 concurrent rung-4s rather than flooding the human.

---

## 5. The Loop (software factory)

```
OBJECTIVE
  └─> REQUIREMENTS (REQ-NN, traceable)            [existing requirements.md]
       └─> SPEC per phase + EVAL CONTRACT (locked) [A1/A3, authored together]
            └─> PLAN  (planner reads contract,      [A2: de-orphan]
                       emits acceptance_criteria)
                 └─> EXECUTE  (per-task HARD gate    [existing gate + ledger updates]
                       on eval rows; ledger flush
                       per task=commit)
                      └─> VERIFY (evals green +       [coverage gate A7 +
                            coverage + weakening)       weakening detector A6]
                           └─> { next task | HANDOFF } [B: ledger warm; resume]
                                └────────── loop ──────────┘
   ▲                                                    │
   └──── LOOP-CONTROL watches ledger; on non-convergence (D1) climbs the
         escalation ladder (D2); on intent-drift (D3) escalates to human (D4/D5)
```

Self-continuing, eval-gated, context-resilient, and *safe* (it escalates instead of
thrashing). This is the baseline a software factory runs on top of.

---

## 6. Build classification (modify/unify/retire before add — the discipline)

| Action | Asset |
|---|---|
| **NEW (small)** | Work Ledger template + update protocol + read-first contract; Eval-Contract coverage gate; locked-eval weakening detector; `continuation.policy` config; mobile/full-stack scaffolds (RN/Flutter/native) |
| **EXTEND** | `VALIDATION.md` template → Eval Contract (fields A4, locked_hash); `gsd-planner` → read contract, emit acceptance_criteria; `gsd-context-monitor.js` → orchestrate handoff; `autonomous.md` → task-boundary flush + loop-control ladder; `resume-project.md` → ledger read-first + git cross-check; `.continue-here.md` → ESCALATION block; `STATE.md` → ledger frontmatter; execute-phase post-wave gate → hard |
| **RETIRE / MERGE** | `validate-phase` + `eval-review` → one go/no-go `eval-verify` verdict (contract coverage + weakening + green) |

---

*Next: `03-build-plan.md` turns this into ordered, file-level tasks (feeds LEDGER Phase 1).
Build order is keystone-first: **the ledger**, then eval-contract wiring, then handoff, then
loop-control, then the loop, then mobile — dogfooding a forced handoff as soon as the spine
exists (per advisor: prove the seams before writing 40 files).*
