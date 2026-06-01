<purpose>
Clarify WHAT a phase delivers through a Socratic interview loop with quantitative ambiguity scoring.
Produces a SPEC.md with falsifiable requirements that discuss-phase treats as locked decisions.

This workflow handles "what" and "why" — discuss-phase handles "how".
</purpose>

<ambiguity_model>
Score each dimension 0.0 (completely unclear) to 1.0 (crystal clear):

| Dimension         | Weight | Minimum | What it measures                                  |
|-------------------|--------|---------|---------------------------------------------------|
| Goal Clarity      | 35%    | 0.75    | Is the outcome specific and measurable?           |
| Boundary Clarity  | 25%    | 0.70    | What's in scope vs out of scope?                  |
| Constraint Clarity| 20%    | 0.65    | Performance, compatibility, data requirements?    |
| Acceptance Criteria| 20%   | 0.70    | How do we know it's done?                         |

**Ambiguity score** = 1.0 − (0.35×goal + 0.25×boundary + 0.20×constraint + 0.20×acceptance)

**Gate:** ambiguity ≤ 0.20 AND all dimensions ≥ their minimums → ready to write SPEC.md.

A score of 0.20 means 80% weighted clarity — enough precision that the planner won't silently make wrong assumptions.
</ambiguity_model>

<interview_perspectives>
Rotate through these perspectives — each naturally surfaces different blindspots:

**Researcher (rounds 1–2):** Ground the discussion in current reality.
- "What exists in the codebase today related to this phase?"
- "What's the delta between today and the target state?"
- "What triggers this work — what's broken or missing?"

**Simplifier (round 2):** Surface minimum viable scope.
- "What's the simplest version that solves the core problem?"
- "If you had to cut 50%, what's the irreducible core?"
- "What would make this phase a success even without the nice-to-haves?"

**Boundary Keeper (round 3):** Lock the perimeter.
- "What explicitly will NOT be done in this phase?"
- "What adjacent problems is it tempting to solve but shouldn't?"
- "What does 'done' look like — what's the final deliverable?"

**Failure Analyst (round 4):** Find the edge cases that invalidate requirements.
- "What's the worst thing that could go wrong if we get the requirements wrong?"
- "What does a broken version of this look like?"
- "What would cause a verifier to reject the output?"

**Seed Closer (rounds 5–6):** Lock remaining undecided territory.
- "We have [dimension] at [score] — what would make it completely clear?"
- "The remaining ambiguity is in [area] — can we make a decision now?"
- "Is there anything you'd regret not specifying before planning starts?"
</interview_perspectives>

<process>

## Step 1: Initialize

```bash
INIT=$(node "/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/bin/gsd-tools.cjs" init phase-op "${PHASE}")
if [[ "$INIT" == @file:* ]]; then INIT=$(cat "${INIT#@file:}"); fi
```

Parse JSON for: `phase_found`, `phase_dir`, `phase_number`, `phase_name`, `phase_slug`, `padded_phase`, `state_path`, `requirements_path`, `roadmap_path`, `planning_path`, `response_language`, `commit_docs`.

**If `response_language` is set:** All user-facing text in this workflow MUST be in `{response_language}`. Technical terms, code, and file paths stay in English.

**If `phase_found` is false:**
```
Phase [X] not found in roadmap.
Use /gsd-progress to see available phases.
```
Exit.

**Check for existing SPEC.md:**
```bash
ls ${phase_dir}/*-SPEC.md 2>/dev/null | grep -v AI-SPEC | head -1 || true
```

If SPEC.md already exists:

**If `--auto`:** Auto-select "Update it". Log: `[auto] SPEC.md exists — updating.`

**Otherwise:** Use AskUserQuestion:
- header: "Spec"
- question: "Phase [X] already has a SPEC.md. What do you want to do?"
- options:
  - "Update it" — Revise and re-score
  - "View it" — Show current spec
  - "Skip" — Exit (use existing spec as-is)

If "View": Display SPEC.md, then offer Update/Skip.
If "Skip": Exit with message: "Existing SPEC.md unchanged. Run /gsd-discuss-phase [X] to continue."
If "Update": Load existing SPEC.md, continue to Step 3.

## Step 2: Scout Codebase

**Read these files before any questions:**
- `{requirements_path}` — Project requirements
- `{state_path}` — Decisions already made, current phase, blockers
- ROADMAP.md phase entry — Phase description, goals, canonical refs

**Grep the codebase** for code/files relevant to this phase goal. Look for:
- Existing implementations of similar functionality
- Integration points where new code will connect
- Test coverage gaps relevant to the phase
- Prior phase artifacts (SUMMARY.md, VERIFICATION.md) that inform current state

**Synthesize current state** — the grounded baseline for the interview:
- What exists today related to this phase
- The gap between current state and the phase goal
- The primary deliverable: what file/behavior/capability does NOT exist yet?

Confirm your current state synthesis internally. Do not present it to the user yet — you'll use it to ask precise, grounded questions.

## Step 3: First Ambiguity Assessment

Before questioning begins, score the phase's current ambiguity based only on what ROADMAP.md and REQUIREMENTS.md say:

```
Goal Clarity:       [score 0.0–1.0]
Boundary Clarity:   [score 0.0–1.0]
Constraint Clarity: [score 0.0–1.0]
Acceptance Criteria:[score 0.0–1.0]

Ambiguity: [score] ([calculate])
```

**If `--auto` and initial ambiguity already ≤ 0.20 with all minimums met:** Skip interview — derive SPEC.md directly from roadmap + requirements. Log: `[auto] Phase requirements are already sufficiently clear — generating SPEC.md from existing context.` Jump to Step 6.

**Otherwise:** Continue to Step 4.

## Step 4: Socratic Interview Loop

**Max 6 rounds.** Each round: 2–3 questions max. End round after user responds.

**Round selection by perspective:**
- Round 1: Researcher
- Round 2: Researcher + Simplifier
- Round 3: Boundary Keeper
- Round 4: Failure Analyst
- Rounds 5–6: Seed Closer (focus on lowest-scoring dimensions)

**After each round:**
1. Update all 4 dimension scores from the user's answers
2. Calculate new ambiguity score
3. Display the updated scoring:

```
After round [N]:
  Goal Clarity:       [score] (min 0.75) [✓ or ↑ needed]
  Boundary Clarity:   [score] (min 0.70) [✓ or ↑ needed]
  Constraint Clarity: [score] (min 0.65) [✓ or ↑ needed]
  Acceptance Criteria:[score] (min 0.70) [✓ or ↑ needed]
  Ambiguity: [score] (gate: ≤ 0.20)
```

**Gate check after each round:**

If gate passes (ambiguity ≤ 0.20 AND all minimums met):

**If `--auto`:** Jump to Step 6.

**Otherwise:** AskUserQuestion:
- header: "Spec Gate Passed"
- question: "Ambiguity is [score] — requirements are clear enough to write SPEC.md. Proceed?"
- options:
  - "Yes — write SPEC.md" → Jump to Step 6
  - "One more round" → Continue interview
  - "Done talking — write it" → Jump to Step 6

**If max rounds reached (6) and gate not passed:**

**If `--auto`:** Write SPEC.md anyway — flag unresolved dimensions. Log: `[auto] Max rounds reached. Writing SPEC.md with [N] dimensions below minimum. Planner will need to treat these as assumptions.`

**Otherwise:** AskUserQuestion:
- header: "Max Rounds"
- question: "After 6 rounds, ambiguity is [score]. [List dimensions still below minimum.] What would you like to do?"
- options:
  - "Write SPEC.md anyway — flag gaps" → Write SPEC.md, mark unresolved dimensions in Ambiguity Report
  - "Keep talking" → Continue (no round limit from here)
  - "Abandon" → Exit without writing

**If `--auto` mode throughout:** Replace all AskUserQuestion calls above with Claude's recommended choice. Log decisions inline. Apply the same logic as `--auto` in discuss-phase.

**Text mode (`workflow.text_mode: true` or `--text` flag):** Use plain-text numbered lists instead of AskUserQuestion TUI menus.

## Step 5: (covered inline — ambiguity scoring is per-round)

## Step 6: Generate SPEC.md

Use the SPEC.md template from @/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/templates/spec.md.

**Requirements for every requirement entry:**
- One specific, testable statement
- Current state (what exists now)
- Target state (what it should become)
- Acceptance criterion (how to verify it was met)

**Vague requirements are rejected:**
- ✗ "The system should be fast"
- ✗ "Improve user experience"
- ✓ "API endpoint responds in < 200ms at p95 under 100 concurrent requests"
- ✓ "CLI command exits with code 1 and prints to stderr on invalid input"

**Count requirements.** The display in discuss-phase reads: "Found SPEC.md — {N} requirements locked."

**Boundaries must be explicit lists:**
- "In scope" — what this phase produces
- "Out of scope" — what it explicitly does NOT do (with brief reasoning)

**Acceptance criteria must be pass/fail checkboxes** — no "should feel good" or "looks reasonable."

**If any dimensions are below minimum**, mark them in the Ambiguity Report with: `⚠ Below minimum — planner must treat as assumption`.

Write to: `{phase_dir}/{padded_phase}-SPEC.md`

## Step 6.5: Author + Lock the Eval Contract (mandatory)

> This is the eval-first forcing function: the contract that *proves* each requirement is
> authored **with the spec, before the plan**, and **locked** so it can gate execution. The
> full procedure (the normalized-rows lock definition, the coverage gate, the draft fallback)
> lives in one place — `@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/references/eval-first.md`
> §2.1 — so spec-phase, discuss-phase, and verify-phase all use the *same* lock. spec-phase is
> the primary home; discuss-phase carries an identical fallback for projects that skip
> spec-phase.

Check whether the eval-first gate is active:
```bash
REQUIRE_CONTRACT=$(node "/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/bin/gsd-tools.cjs" query config-get eval_first.require_contract 2>/dev/null || echo "false")
```

**If `REQUIRE_CONTRACT` is not `true`:** skip this step entirely (behave exactly as before —
no contract authored, no gate). Continue to Step 7.

**If `REQUIRE_CONTRACT` is `true`:** Read `references/eval-first.md` §2.1 and execute its
**authoring & lock procedure** verbatim. In summary:

1. **Determine the in-scope REQ set** — the phase's `REQ-NN` IDs, the same IDs plan-phase uses
   as `phase_req_ids`, **not** the SPEC.md prose. `init phase-op` (Step 1) does **not** expose
   `phase_req_ids`, so read `{requirements_path}` (`.planning/REQUIREMENTS.md`) and select the
   `REQ-NN` entries scoped to this phase, cross-referenced with the phase's ROADMAP entry
   (`{roadmap_path}`):
   ```bash
   cat "${requirements_path}" 2>/dev/null || true   # select the REQ-NN ids in this phase's scope
   ```
   (Fall back to the `REQ-NN` IDs this SPEC.md's requirements reference if REQUIREMENTS.md has
   no phase-scoped REQs.)
2. **Author** `{phase_dir}/{padded_phase}-EVAL-CONTRACT.md` from
   `@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/templates/eval-contract.md` —
   one behavioral-acceptance `## Rows` entry per provable claim (altitude per the template's
   `<altitude>`), each row tagged with a real in-scope `req_ref`. Set frontmatter
   `status: draft` and `coverage.requirements` to the in-scope REQ set.
3. **Run the coverage gate (§3):** fill `coverage.uncovered_reqs` (in-scope REQs with no row)
   and `coverage.orphan_rows` (rows whose `req_ref` is not in scope); set `coverage.rows_total`.
4. **Lock or stay draft:**
   - **Both arrays empty →** set `status: locked`, `locked_at`, and compute `locked_hash` with
     the §2.1 command:
     ```bash
     CONTRACT="${phase_dir}/${padded_phase}-EVAL-CONTRACT.md"
     LOCKED_HASH=$(grep -E '^[[:space:]]*\|[[:space:]]*EC' "$CONTRACT" \
       | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' \
       | shasum -a 256 | awk '{print $1}')
     ```
     Write `locked_hash: '${LOCKED_HASH}'` into the frontmatter.
   - **Either array non-empty →** leave `status: draft`, do **not** set `locked_hash`, and tell
     the user which REQs need a row / which rows are orphaned. The phase cannot be planned until
     it locks — fix the contract (or the requirements) and re-run `/gsd-spec-phase ${phase_number}`.

Display the contract status:
```
Eval contract: {locked | DRAFT — N uncovered REQ, M orphan rows}
  {phase_dir}/{padded_phase}-EVAL-CONTRACT.md
```

## Step 7: Commit

```bash
git add "${phase_dir}/${padded_phase}-SPEC.md"
# Include the eval contract when it was authored (Step 6.5):
[ -f "${phase_dir}/${padded_phase}-EVAL-CONTRACT.md" ] && git add "${phase_dir}/${padded_phase}-EVAL-CONTRACT.md"
git commit -m "spec(phase-${phase_number}): add SPEC.md for ${phase_name} — ${requirement_count} requirements (#2213)"
```

If `commit_docs` is false: Skip commit. Note that SPEC.md (and the eval contract, if authored) was written but not committed.

## Step 8: Wrap Up

Display:

```
SPEC.md written — {N} requirements locked.

  Phase {X}: {name}
  Ambiguity: {final_score} (gate: ≤ 0.20)

Next: /gsd-discuss-phase {X}
  discuss-phase will detect SPEC.md and focus on implementation decisions only.
```

</process>

<critical_rules>
- Every requirement MUST have current state, target state, and acceptance criterion
- Boundaries section is MANDATORY — cannot be empty
- "In scope" and "Out of scope" must be explicit lists, not narrative prose
- Acceptance criteria must be pass/fail — no subjective criteria
- SPEC.md is NEVER written if the user selects "Abandon"
- Do NOT ask about HOW to implement — that is discuss-phase territory
- Scout the codebase BEFORE the first question — grounded questions only
- Max 2–3 questions per round — do not frontload all questions at once
- When `eval_first.require_contract` is true: author the eval contract (Step 6.5) and lock it
  via the **single** procedure in `references/eval-first.md` §2.1 — never invent a different
  normalization. A contract that fails the coverage gate stays `draft` (work preserved) and
  blocks plan-phase until fixed; do NOT lock a contract with uncovered REQs or orphan rows.
</critical_rules>

<success_criteria>
- Codebase scouted and current state understood before questioning
- All 4 dimensions scored after every round
- Gate passed OR user explicitly chose to write despite gaps
- SPEC.md contains only falsifiable requirements
- Boundaries are explicit (in scope / out of scope with reasoning)
- Acceptance criteria are pass/fail checkboxes
- SPEC.md committed atomically (when commit_docs is true)
- When `eval_first.require_contract` is true: `{padded_phase}-EVAL-CONTRACT.md` authored from the
  template; coverage gate run (`uncovered_reqs`/`orphan_rows` filled); contract `status: locked`
  with a computed `locked_hash` when the gate is clean, else `status: draft` with the user told
  which REQs/rows to fix; contract committed alongside SPEC.md (when commit_docs is true)
- User directed to /gsd-discuss-phase as next step
</success_criteria>
