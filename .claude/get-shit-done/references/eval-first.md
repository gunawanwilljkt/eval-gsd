# Reference: Eval-First Spec-Driven Development

How GSD makes evaluation a **first-class, early, integrated, gating** part of every phase —
not a downstream audit. The artifact is @.claude/get-shit-done/templates/eval-contract.md.
This reference is the operational protocol: where it's authored, how it locks, how the
existing executor gate enforces it, and how verify-phase keeps it honest.

**Core principle — unify the CONTRACT, keep the EVALUATORS plural.** One authored contract
per phase; three evaluators behind it: the deterministic per-task gate (Code), an independent
judge (Judge), and human-UAT (Human). GSD's deliberate *generation ≠ evaluation* separation
is preserved — the contract is pre-committed before code, and the verdict layer stays
independent of the generator.

This supersedes the *contract role* of `VALIDATION.md` and the eval rows of `AI-SPEC §5`. The
post-hoc auditors `validate-phase` and `eval-review` are **merged** into one go/no-go pass at
verify-phase (see §5).

---

## 1. Lifecycle & where it plugs into existing workflows

```
spec/discuss ── author EVAL-CONTRACT.md (MANDATORY) ── coverage gate ── lock (hash)
     │                                                                      │
plan-phase ── planner READS contract ── emits `gate` Code rows as ──────────┘
     │         task <acceptance_criteria>;  sample_rate → wave/pre-verify cadence
execute ── executor's EXISTING per-task HARD GATE runs the criteria ── ledger records evidence
     │
verify-phase (= eval-verify) ── coverage + weakening + gaming checks + Judge/Human rows ── verdict
```

The only genuinely new machinery is the **coverage gate** (§3) and the **weakening/gaming
detector** (§4). Everything else is wiring existing assets:
- `gsd-planner` gains a read of the contract and emits acceptance_criteria (de-orphans the
  previously-ignored AI-SPEC §5).
- `execute-plan`'s acceptance_criteria HARD GATE (already runs grep/CLI commands and BLOCKs
  the next task on failure — execute-plan.md §"HARD GATE") needs **no change**; it enforces
  the contract for free once the planner emits the rows.
- `verify-phase` gains the coverage + weakening + gaming checks and absorbs validate/eval-review.

## 2. Authoring at spec time (mandatory)

- Authored during `/gsd-spec-phase` (or `/gsd-discuss-phase` if no spec-phase) — **before**
  the plan. A phase cannot be planned without a `locked` contract.
- Writing the eval first is a forcing function: if you can't state what would *prove* a
  requirement, the requirement is under-specified — fix the spec, not the eval.
- Altitude = behavioral acceptance, never unit (see template `<altitude>`). This is what
  makes spec-time authoring possible before code exists.
- Measurement split keeps it cheap & mandatory: Code for the ~80% structural, Judge only for
  subjective quality, Human for experience/high-stakes (template `<measurement_split>`).
- **Mobile / full-stack phases:** the per-platform runnable commands that become `Code` rows
  (RN/Flutter/native build·typecheck·unit·e2e-on-simulator; cross-stack e2e smokes) live in
  @.claude/get-shit-done/references/mobile-scaffold.md — same split (deterministic Code for the
  ~80%, `warn` skip-able simulator/device smokes, `Human` for device feel & store review).

## 2.1. The authoring & lock procedure (single source of truth)

Both `/gsd-spec-phase` (primary home) and `/gsd-discuss-phase` (fallback when a project skips
spec-phase) author and lock the contract by invoking **this exact procedure** — it lives here,
once, so the lock is reproducible and `verify-phase`'s weakening detector (§4) can recompute
the same hash. Run it after the phase's requirements are settled, before the phase is planned.

**Inputs:**
- `{phase_dir}` + `{padded_phase}` — the phase directory and zero-padded number.
- **The in-scope REQ set** — the phase's requirement IDs (`REQ-NN`). This is the *same* set
  plan-phase consumes as `phase_req_ids`, but the spec/discuss `init.phase-op` JSON does **not**
  expose `phase_req_ids` (only `init.plan-phase` / `init.execute-phase` do — verified). So in
  the spec/discuss context, resolve it by **reading `{requirements_path}` (`.planning/REQUIREMENTS.md`)
  and selecting the `REQ-NN` entries scoped to this phase** (cross-referenced with the phase's
  ROADMAP entry, which `init.phase-op` gives you as `roadmap_path`). It is **not** the SPEC.md
  prose. If REQUIREMENTS.md has no phase-scoped REQs, fall back to the `REQ-NN` IDs the spec /
  discussion just locked.

**Steps:**
1. **Author** `{phase_dir}/{padded_phase}-EVAL-CONTRACT.md` from
   `@.claude/get-shit-done/templates/eval-contract.md`. Fill `## Rows` with one behavioral-
   acceptance row per provable claim (altitude per the template's `<altitude>`), every row
   carrying an `objective_ref`, a `req_ref` that is a real in-scope `REQ-NN`, a `measurement`
   (Code/Judge/Human), a runnable `command_or_rubric`, and a `severity` (`gate` | `warn`).
   Set frontmatter `status: draft`, `phase`, `coverage.requirements: [<the in-scope REQ set>]`.
2. **Run the coverage gate (§3).** Compute, against the in-scope REQ set:
   - `uncovered_reqs` = in-scope REQs with **zero** rows whose `req_ref` names them.
   - `orphan_rows` = row ids whose `req_ref` is **not** an in-scope REQ.
   Write both arrays into frontmatter `coverage`. Set `coverage.rows_total` to the row count.
3. **Lock — only if both arrays are empty.**
   - **If `uncovered_reqs` OR `orphan_rows` is non-empty:** leave `status: draft`, do **not**
     set `locked_hash`, and tell the user exactly which REQs need a row / which rows are
     orphaned. Work is preserved; the phase cannot be planned until it locks (plan-phase §1.6
     gate). This is the forcing function — fix the contract (or the requirements), re-run.
   - **If both are empty:** set `status: locked`, `locked_at: {YYYY-MM-DD}`, and compute
     `locked_hash` with the **normalized-rows** definition below.

**`locked_hash` — the normalized-rows definition (exact, reproducible):** the hash is the
sha256 of the contract's **data rows** — every line of the `## Rows` table that begins (after
optional leading whitespace) with `| EC` — with each such line's **leading and trailing
whitespace trimmed**, joined by single newlines, in file order. Header row, separator row
(`|---|`), prose, and frontmatter are excluded. (Anchoring on `| EC` data rows makes the hash
robust to the table's column count and to surrounding markdown.) Exact command:

```bash
CONTRACT="{phase_dir}/{padded_phase}-EVAL-CONTRACT.md"
LOCKED_HASH=$(grep -E '^[[:space:]]*\|[[:space:]]*EC' "$CONTRACT" \
  | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' \
  | shasum -a 256 | awk '{print $1}')
echo "$LOCKED_HASH"   # write into frontmatter: locked_hash: '<value>'
```

**Property:** the hash is over row *content*, normalized only for outer whitespace — so
reordering, deleting, weakening, or adding a row changes it, while a pure re-indent of the
whole table line does not. Reformatting a row's *internal* spacing **does** change the hash;
that is acceptable, because any deliberate edit to a locked row must go through an explicit
re-lock anyway (§4, "explicit renegotiation"). The same command run by `verify-phase` (§4,
weakening detector) on the shipped contract must reproduce the stored `locked_hash`.

> Reference check (reproducible): run the command above on the dogfood plan's rows
> (`dogfood/.planning/PLAN.md`, the `| EC-1 … | EC-2 …` lines) → it yields
> `637f08b2bab84a805e98f087c9894ff942269b5c1951dc15e035fc6da498a1cd` (338 normalized bytes).

## 3. The coverage gate (intent ⇄ eval bijection)

Run before locking, and again at verify-phase. Pure function of the contract + REQUIREMENTS.md:
- **Uncovered REQ:** every `REQ-NN` in scope must map to ≥1 contract row. Any REQ with zero
  rows → `uncovered_reqs` non-empty → **cannot lock**. (This is how *intent with no eval* —
  the classic spec-drift-from-intent hole — is caught.)
- **Orphan row:** every row's `req_ref` must resolve to a real REQ. Dangling → `orphan_rows`
  non-empty → cannot lock.
- Result: `objective → REQ → eval` is a verified chain in both directions. Passing evals can
  now be *attributed to intent*, and unmet intent surfaces as a coverage hole.

## 4. Keeping evals honest (the independence layer)

Because the contract **gates** execution, it must resist the generator grading itself:
- **Lock before code:** `status: locked` + `locked_hash` (sha256 of the **normalized rows** —
  defined exactly in §2.1) is set at spec time. `plan-phase` refuses a `draft` contract.
- **Weakening detector (verify-phase):** recompute the hash; diff shipped acceptance_criteria
  vs the locked rows. Any row deleted, `skip`-ped, or loosened → flag. (This needs the locked
  baseline to diff against — it is real work, not a free reuse of `audit_test_quality`,
  though it shares that auditor's machinery.)
- **Gaming detector (git-derivable):** for each `gate` row, if `git show <green_commit>
  --stat` shows the row's own eval/test file changed in the *same commit* that turned it
  green → the test was bent to the output. Flag, don't pass. (Enforced by the ledger's
  two-commit convention: work commit separate from any eval edit.)
- **Independent judge:** `Judge` rows are scored by a different agent than the code author;
  deterministic rows need no judge (command output is the verdict).
- **Explicit renegotiation:** a wrong locked eval is changed via a logged decision that
  **re-locks** the hash — never silently weakened.

## 5. Merged verdict at verify-phase (retire validate-phase + eval-review)

verify-phase becomes the single go/no-go "eval-verify":
1. Coverage gate (§3) passes.
2. Weakening + gaming checks (§4) clean.
3. All `severity: gate` rows green (Code from ledger evidence; Judge scored now; Human via
   `{NN}-UAT.md`).
4. `warn` rows reported, non-blocking.
→ Green = phase verified. Any gate red / coverage hole / weakening = **blocked** (this is
already verify-phase's posture: "a phase cannot be verified if tests fail").

`validate-phase` (Nyquist) and `eval-review` are retired as separate commands; their useful
parts (sampling cadence, AI-quality dimensions) live in the contract's `sample_rate` and
`Judge` rows respectively.

## 6. Relationship to the Work Ledger

The ledger records, per task, the `eval_rows` it must turn green and `evidence`
(`passing_eval_ids` + `commit_sha`). Loop-control reads these to detect non-convergence
(S1: consecutive eval-gate failures). So the eval contract and the ledger are two halves of
one loop: the contract says *what green means*; the ledger tracks *how close we are and
whether we're stuck*. See @.claude/get-shit-done/references/work-ledger.md.

## 7. Anti-patterns
- ❌ Authoring evals after code (audit, not eval-first) — author at spec time.
- ❌ Unit-altitude rows that bind to unchosen implementation — behavioral acceptance only.
- ❌ A judge on plain CRUD — deterministic Code row instead (cheap, objective).
- ❌ Editing an eval in the same commit that makes it pass — gaming; two commits.
- ❌ Weakening a locked row silently — renegotiate + re-lock with a logged decision.
- ❌ Treating verify-phase evals as advisory — gate rows BLOCK.
