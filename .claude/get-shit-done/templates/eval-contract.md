# Eval Contract Template

Template for `.planning/phases/{NN}-{slug}/{NN}-EVAL-CONTRACT.md` — the **first-class,
spec-time, locked** definition of how we will *prove* a phase did what the spec and the
*intent* asked. Evals are not a later audit; the contract is authored **with the spec**,
before code, and its rows become the gate the executor already enforces.

It unifies and supersedes the *contract role* of the old `VALIDATION.md` (req→command map)
and the eval rows of `AI-SPEC §5`. Evaluators stay plural (deterministic gate / independent
judge / human-UAT); only the **contract** is unified.

> Protocol it plugs into: @.claude/get-shit-done/references/eval-first.md
> (authoring at spec time, locking, the planner wiring, the verify-phase coverage + weakening
> gates, the measurement split).

---

## File Template

```markdown
---
eval_contract_version: '1.0'
phase: '{NN}-{slug}'
status: locked            # draft | locked   (must be `locked` before plan-phase runs)
locked_hash: '{sha256 of the normalized rows below — set when status→locked}'
locked_at: '{YYYY-MM-DD}'
coverage:                 # filled by the coverage gate; every REQ must map to ≥1 row
  requirements: [REQ-01, REQ-02]
  rows_total: 0
  uncovered_reqs: []      # MUST be empty to lock
  orphan_rows: []         # rows whose req_ref maps to nothing — MUST be empty to lock
---

# Phase {NN} — Eval Contract

Intent (one line, from the objective): "{what success means for a user, in plain language}"

## Rows

Each row is one provable claim. `objective_ref → req_ref` makes every eval traceable back to
intent. `measurement` picks the cheapest honest evaluator. `command_or_rubric` is runnable
(Code) or a scored rubric (Judge/Human). `severity: gate` rows BLOCK; `warn` rows inform.

| id | objective_ref | req_ref | behavior (acceptance altitude) | measurement | command_or_rubric | sample_rate | severity |
|----|---------------|---------|--------------------------------|-------------|-------------------|-------------|----------|
| EC-1 | {obj} | REQ-01 | POST /sessions with valid body → 201 + body matches schema S | Code | `curl -s -o /tmp/r -w '%{http_code}' ... | grep 201 && jsonschema -i /tmp/r schema.json` | per-task | gate |
| EC-2 | {obj} | REQ-02 | migration applies cleanly on an empty DB | Code | `make db.reset && make db.migrate` (exit 0) | per-task | gate |
| EC-3 | {obj} | REQ-03 | the "session expired" message is clear & non-technical | Judge | rubric R-1 (PASS: plain-language, actionable; FAIL: stack trace / jargon) | pre-verify | gate |
| EC-4 | {obj} | REQ-03 | checkout *feels* responsive on a real device | Human | UAT step U-1 | pre-verify | warn |

## Judge Rubrics (only for `measurement: Judge` rows)

### R-1 — {name}
- PASS: {specific acceptable behavior, in domain language}
- FAIL: {specific unacceptable behavior, in domain language}
- Calibration: scored by an INDEPENDENT judge agent (not the executor); ≥N reference
  examples; target ≥0.7 agreement with human spot-checks before this row is trusted.

## Human-UAT rows (only for `measurement: Human`)
Carried into `{NN}-UAT.md` at verify-work. The human lens is irreplaceable for
experience/high-stakes; do not fake it with a deterministic check.

## Reference dataset (if any Judge rows)
10–20 high-quality examples (input → expected disposition) under
`.planning/phases/{NN}-{slug}/eval-data/`. Built as a task in the plan, not after.
```

<purpose>

The user's thesis: *"AI can generate code flawlessly but still needs evals to confirm it
follows the spec and the intention."* This artifact is that confirmation, made first-class:

- **Early:** authored at spec time, *before* the plan and code. Writing the eval first forces
  the spec to be concrete ("what would prove this?").
- **Alongside, not separate:** its `severity: gate` Code rows are emitted by the planner as
  task `<acceptance_criteria>`, which the executor **already runs and hard-gates on** every
  task. Red→green on contract rows literally *is* task progress. No separate "eval phase."
- **Intent, not just spec:** every row chains `objective → REQ → eval`. The coverage gate
  (below) flags any REQ with no eval and any eval with no REQ — that bijection is how
  spec-drift-from-intent is caught.

</purpose>

<altitude>

**Write evals at BEHAVIORAL ACCEPTANCE altitude, not unit altitude.** You can write these
before any code exists; they bind to *behavior*, not to an implementation you haven't chosen:
- ✅ "POST /x with body B → 201 + schema S", "migration applies on clean DB", "route /dash
  renders without error", "CLI `foo --bar` exits 0 and prints a valid plan".
- ❌ "`computeTotal()` returns 42", "the helper is called twice" — couples the contract to an
  unchosen implementation; brittle and premature.

</altitude>

<measurement_split>

Pick the **cheapest honest** evaluator so "evals for ALL code" stays affordable and mandatory:
- **Code (the ~80%)** — structure/contract: schema validity, status codes, migrations,
  navigation reachable, build/lint/typecheck pass, file/route exists. Deterministic, fast,
  objective. Default here.
- **Judge** — *subjective quality* only: "is the error message clear", "is the summary
  faithful". Calibrated, scored by an independent agent. Never put plain CRUD behind a judge.
- **Human (UAT)** — experience & high-stakes: feel, safety, irreversible actions.

</measurement_split>

<independence>

The contract gates execution, so it must stay honest (no generator self-grading):
1. **Lock before code.** `status: locked` + `locked_hash` (a sha256 of the normalized rows)
   is set at spec time. plan-phase refuses to proceed on a `draft` contract.
2. **Weakening detection.** verify-phase recomputes the hash and diffs shipped evals vs the
   locked baseline; any row deleted / skipped / loosened is flagged (not silently accepted).
3. **Gaming detection.** A `gate` row that went green in the *same commit* that edited its own
   eval/test file → flagged (test bent to output). Hence the two-commit convention (work
   commit, then ledger flush) in the ledger protocol.
4. **Independent judge.** Judge rows are scored by a different agent than the one that wrote
   the code. Deterministic rows need no judge — the command output is the verdict.

If a locked eval genuinely turns out wrong, it is **renegotiated explicitly** (a logged
decision that re-locks the hash), never quietly weakened.

</independence>

<lifecycle>

- **Authored:** at spec time (during `/gsd-spec-phase` or `/gsd-discuss-phase`), **mandatory
  for every phase** (not just AI phases). A phase without an eval contract cannot be planned.
- **Locked:** before `/gsd-plan-phase`. The coverage gate must pass (no uncovered REQ, no
  orphan rows) to lock.
- **Consumed:** `gsd-planner` reads it and emits `gate` Code rows as task
  `<acceptance_criteria>`; `sample_rate` drives per-wave / pre-verify cadence.
- **Enforced:** the executor's existing per-task HARD GATE runs the criteria; the ledger
  records each row's pass/fail as evidence.
- **Verified:** `/gsd-verify-phase` (merged eval-verify) runs the coverage + weakening +
  gaming checks and the Judge/Human rows for one go/no-go verdict.

</lifecycle>

<size_constraint>

One row per provable claim; aim for the smallest set that fully covers the REQs. If a phase
has zero `gate` rows it is almost certainly under-specified — what would prove it works?

</size_constraint>
