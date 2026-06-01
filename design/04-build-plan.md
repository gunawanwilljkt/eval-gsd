# 04 — Build Plan: the remaining wiring (resumable task list)

> This is the persistent, file-level task list for finishing the framework. The hard,
> novel core is **built and proven** (Work Ledger + Eval Contract + the auto-handoff hook +
> the dogfood). What remains is **wiring those into the existing GSD workflows** — lower-risk
> but careful work, because the targets are large existing files in a 67-command framework.
>
> Each task lists: the file(s), the exact change, and an **acceptance** (its own eval, in the
> spirit of the framework). Do them in order; W1–W2 unlock the eval-first loop, W3–W4 unlock
> the autonomous-handoff loop end-to-end, W5–W6 close the safety loop, W7 registers, W8 is a
> separate deliverable. A fresh session: read `design/LEDGER.md`, then this file, then start
> at the first `todo`.

## Status legend
`[ ] todo` · `[~] doing` · `[x] done` · `[!] blocked`

---

## DONE (built + proven this session)
- [x] Work Ledger — `templates/ledger.md` (two-tier) + `references/work-ledger.md` (single-writer, git-truth, checkpoint discipline, v1 loop-control). Refined ×4 from dogfood.
- [x] Eval Contract — `templates/eval-contract.md` + `references/eval-first.md` (spec-time, locked, coverage gate, independence layer, measurement split).
- [x] Auto-handoff trigger — `hooks/gsd-context-monitor.js` upgraded (advise→orchestrate; ledger-aware WARNING/CRITICAL; tested 3 paths) + `templates/config.json` (`continuation.policy`, `eval_first`).
- [x] Dogfood — fresh-context agent resumed an eval-gated build from the ledger alone (`design/03-dogfood-proof.md`).

---

## W1 — Wire the planner to the eval contract  *(highest leverage; unlocks eval-first)*  — [x] done
> Evidence (2026-06-01): `agents/gsd-planner.md` got 4 additive edits — (1) `<required_reading>` block (eval-first.md always; `{NN}-EVAL-CONTRACT.md` if present); (2) contract + AI-SPEC reads folded into `gather_phase_context`; (3) new `emit_acceptance_criteria` step (select gate+Code rows, map each to exactly one task by `req_ref`/behavior, emit `command_or_rubric` verbatim into the task's `<acceptance_criteria>` XML block additively, carry `<eval_rows>`, de-orphan AI-SPEC §5, with coverage+uniqueness self-check); (4) self-check line in `<success_criteria>`. Backward-compatible: no contract → step skipped, planner unchanged. Dry trace verified against dogfood EC-1/EC-2: EC-1→T1, EC-2→T2, commands byte-identical (backticks aside). Validator check (advisor item): `bin/lib/verify.cjs` `verify.plan-structure` is presence-only (probes `<name>`/`<action>`/etc.) with NO closed-set enforcement → the new `<eval_rows>` task child survives a live planner run, won't be flagged/stripped. AI-SPEC §5 de-orphan = honest best-effort: §5's Dimensions table (`Dimension|Rubric|Measurement|Priority`) has no `req_ref`/`command_or_rubric`/`severity`, so only §5 Code dimensions with a real command are emitted; the rest are carried to verify-phase and the planner is told to surface "this AI phase should have an eval contract" rather than invent commands (contract supersedes §5). STRUCTURAL + dry-trace only — no live planner run; the non-trivial "REQ spans multiple tasks" disambiguation and §5 path are unexercised by a real run.
- **File:** `.claude/agents/gsd-planner.md`
- **Change:** add `references/eval-first.md` + the phase `{NN}-EVAL-CONTRACT.md` to `<required_reading>`. Add a planning step: for each contract row with `severity: gate` AND `measurement: Code`, emit its `command_or_rubric` as an `<acceptance_criteria>` on the task that satisfies the row's `req_ref`; carry `eval_rows: [EC-..]` onto that task. Also read `AI-SPEC §5` if present and fold its rows into the contract (de-orphan).
- **Why:** the executor *already* runs & hard-gates `<acceptance_criteria>` (execute-plan.md:178-184, verified). This single wire makes evals gate execution for free.
- **Acceptance:** a generated PLAN.md task carries an `<acceptance_criteria>` whose command equals a contract row's `command_or_rubric`, and every `gate`/`Code` row maps to exactly one task.

## W2 — Author + lock the contract at spec time (mandatory)  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W2): the lock
> procedure now lives in **one** durable place so verify-phase (W5) can reproduce it —
> `references/eval-first.md` new **§2.1 "authoring & lock procedure"**: defines the in-scope REQ
> source (phase `REQ-NN` IDs from REQUIREMENTS.md/ROADMAP, NOT SPEC prose), the coverage gate's
> draft fallback (non-empty `uncovered_reqs`/`orphan_rows` → stay `draft`, no hash, tell the user
> which to fix — work preserved), and the **exact normalized-rows `locked_hash`**: sha256 of the
> `## Rows` data lines (lines matching `^\s*\|\s*EC`), each trimmed of outer whitespace, joined by
> newlines — `grep -E '^[[:space:]]*\|[[:space:]]*EC' "$C" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | shasum -a 256`.
> §4 updated to point at §2.1 instead of the vague "sha256(normalized rows)".
> **spec-phase.md** (primary): new **Step 6.5** (between SPEC.md write + commit) gated on
> `eval_first.require_contract` — authors `{NN}-EVAL-CONTRACT.md` from the template, runs the
> coverage gate, locks (or stays draft), commits alongside SPEC.md; `<critical_rules>` +
> `<success_criteria>` extended. **discuss-phase.md** (fallback — REQUIRED because the dogfood and
> any discuss-only project go discuss→plan with no SPEC.md, so with the `require_contract: true`
> default they'd hit an unsatisfiable plan-phase block): new `author_eval_contract` step after
> `write_context`, same §2.1 procedure, **skips if spec-phase already wrote the contract** (no
> overwrite), commits with CONTEXT.md; `eval-first.md` added to `<required_reading>`;
> `<success_criteria>` extended. **plan-phase.md**: new **§1.6 Eval-First Contract Gate** right
> after §1 Initialize (mirrors §1.5 Closed-Phase Gate's hard-stop pattern) — when
> `eval_first.require_contract` is true, BLOCK + exit with a concrete remedy command if the contract
> is missing OR `status` ≠ `locked`; **no-op (exact prior behavior) when the key is absent/false**.
> `commands/gsd/spec-phase.md` needs NO substantive edit (it only delegates `@`-includes the
> workflow). ACCEPTANCE: **executed** — computed the dogfood rows' `locked_hash` =
> `637f08b2bab84a805e98f087c9894ff942269b5c1951dc15e035fc6da498a1cd` (338 normalized bytes,
> reproducible across runs) proving the lock command is real; the plan-phase gate's status
> extraction tested green on synthetic `locked`/`draft` contracts AND the real template's
> inline-comment frontmatter (`status: locked   # …` → `locked`); missing-dir glob → empty →
> BLOCK (correct). STRUCTURAL: the spec-phase/discuss-phase authoring steps and the plan-phase
> gate decision tree are unambiguous (a reader knows exactly when to block). No live
> `/gsd-spec-phase` or `/gsd-plan-phase` run. Code-fence balance verified even in all 4 files.
> ADVISOR-PASS FIXES (2nd advisor call, before flipping done — both backward-compat bugs squarely
> inside W2): (1) **plan-phase §1.6 now skips the gate for research-only/view-only runs**
> (`--research-phase`/`--view` route through the same command, produce NO plan, and for
> `--research-phase N` the phase isn't resolved until §2) — without this, `require_contract: true`
> would block `/gsd-plan-phase --research-phase N` and regress an existing flow, falsifying "additive".
> (2) **discuss-phase `author_eval_contract` now skips only when the existing contract is `status:
> locked`, not merely present** — the file-existence skip left a `draft` unrecoverable for
> discuss-only projects and made §1.6's "re-run /gsd-discuss-phase" remedy a no-op; a `draft` is now
> re-gated + re-locked. (3) **REQ-source corrected**: `roadmap.get-phase --pick requirements` was
> wrong (that verb returns `{found,phase_number,phase_name,goal,mode,success_criteria,section}`, NO
> `requirements` field — verified in `bin/lib/roadmap.cjs`); and `init.phase-op` (spec/discuss) does
> NOT expose `phase_req_ids` (only `init.plan-phase`/`init.execute-phase` do). Fixed all three spots
> to read `{requirements_path}` + cross-ref ROADMAP, SPEC/discussion REQ IDs as fallback. Re-verified
> post-fix: dogfood hash unchanged, fences even, no wrong verb remains.
> NOTE: discuss-phase.md grew to 554 lines; the upstream 500-line workflow-size budget test
> (`tests/workflow-size-budget.test.cjs`, #2551) is NOT shipped in this tree, so nothing enforces
> it here — flag for W7/upstream if that test is later vendored (could move the fallback step body
> to a lazy-loaded mode file then).
- **Files:** `.claude/get-shit-done/workflows/spec-phase.md` (primary) and/or `discuss-phase.md`; `commands/gsd/spec-phase.md`.
- **Change:** add a step that writes `{NN}-EVAL-CONTRACT.md` from `templates/eval-contract.md`, runs the **coverage gate** (no `uncovered_reqs`, no `orphan_rows` vs REQUIREMENTS.md), then sets `status: locked` + computes `locked_hash` (sha256 of normalized rows). Gate `plan-phase` on `status: locked` when `config.eval_first.require_contract` is true.
- **Acceptance:** spec-phase yields a `locked` contract; plan-phase refuses to proceed on a missing/`draft` contract (with `require_contract: true`).

## W3 — Orchestrator writes the ledger from executor returns (single-writer)  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W3): **Executor emits `## LEDGER UPDATE` into SUMMARY.md; orchestrator (main tree) parses the MERGED SUMMARY.md on disk and is the sole writer of `.planning/LEDGER.md`.** Executor side (additive): `agents/gsd-executor.md` new `<ledger_update_return>` block + `<self_check>` step 4 + `<completion_format>` echo + `<success_criteria>` line — appends one `## LEDGER UPDATE` block per task (exact §1 schema, verbatim) after the `## Self-Check:` line, with an explicit "NEVER write/commit LEDGER.md" invariant; `workflows/execute-plan.md` mirror — new `<step name="ledger_update_return">` + `create_summary`/`segment_execution`/`success_criteria` hooks. Orchestrator side: `execute-phase.md` new `<ledger_single_writer>` preamble + work-ledger.md in `<required_reading>`; new **step 5.9 ledger_flush** (parse blocks from merged SUMMARY.md via awk — disk is authoritative, NOT the chat return per #2070/completion-signal fallback; create-if-absent from `templates/ledger.md`, best-effort/non-fatal; merge each field into the task record; gate HEAD recompute on the SAME `TEST_EXIT` as 5.7; commit ONLY the ledger as a separate `chore(ledger):` two-commit). **Hardened step 5.8** from soft "Fix now / Continue" → **block-or-escalate**: auto-mode escalates+pauses (rung 2, records Open Escalation; does NOT advance), interactive requires explicit fix-or-stop (removed the "Continue anyway"); `aggregate_results` gets a **ledger escalation guard** that blocks phase completion/verification when `## Open Escalations` is non-empty. **ACCEPTANCE (structural + field-by-field trace):** the executor's emitted 9-line schema is byte-identical (field names + order) across `gsd-executor.md`, `execute-plan.md`, and canonical `work-ledger.md §1`; orchestrator 5.9 maps each field to a real `templates/ledger.md` Task-Record field — `task`→record id, `status`→status, `commit_sha`→evidence.commit_sha, `passing_eval_ids`→evidence.passing_eval_ids, `failing_eval_ids`+`attempt_summary`→attempts[], `self_check:FAILED`→git-truth not-done gate (§3), `blocker`→blocker. Single-writer **grep-proven**: the only LEDGER.md write/commit anywhere in the execute path is execute-phase 5.9's `cp` (seed) + `chore(ledger): … --files .planning/LEDGER.md`; both executor files mention LEDGER.md ONLY as prohibitions. Fences EVEN in all 3 files. **Structural-only**: no live `/gsd-execute-phase` run — the awk block extraction and the auto-mode escalation path are unexercised by a real wave; only the schema-match + single-writer wiring is proven. Backward-compat: every executor edit is appended text; create-if-absent + non-fatal flush keep a legacy (no-LEDGER.md) project working; the ONLY existing-behavior change is the 5.8 gate (soft→hard), which loop-control mandates.
- **Files:** `workflows/execute-phase.md`, `workflows/execute-plan.md`, `agents/gsd-executor.md`.
- **Change:** executor appends the `## LEDGER UPDATE` block (schema in `references/work-ledger.md §1`) to its result/SUMMARY. Orchestrator parses each return and writes/commits `LEDGER.md` in the **main tree** at each task/wave boundary (create it at init if absent). Harden the post-wave integration-test gate from soft warning → block-or-escalate (loop-control). **Invariant:** subagents never write `LEDGER.md`.
- **Acceptance:** after execute-phase, `LEDGER.md` HEAD reflects current position and each task record has `evidence{commit_sha, passing_eval_ids}`; `git log` shows only the orchestrator committed the ledger.

## W4 — Wire the proven resume protocol into the command  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W4): **`/gsd-resume-work`
> now reads `.planning/LEDGER.md` Tier-1 HEAD FIRST and runs the §3 git-as-ground-truth algorithm;
> the legacy HANDOFF.json/`.continue-here` pair is demoted to a fallback used only when no ledger
> exists.** `workflows/resume-project.md`: added `work-ledger.md` to `<required_reading>`, a
> `<resume_source_priority>` preamble (ledger primary / legacy fallback), and a new **`ledger_resume`
> step** between `initialize` and `load_state` running the algorithm in the exact order — (1) read
> Tier-1 HEAD only, (2) git-verify each `done` task's `commit_sha`
> (`git cat-file -e <sha>^{commit}` + `git merge-base --is-ancestor <sha> HEAD`; missing → demote to
> `doing` + flag; discard uncommitted half-work for an `in_progress` task and re-run idempotently
> from last clean commit; `SUMMARY.md` `## Self-Check: FAILED` → not done), (3) **Open Escalations
> non-empty → surface + PAUSE (stop)**, (4) **terminal `status: complete` → route to closeout (stop)**,
> (5) **only if real work remains: bump `generation` +1 + run the forward-progress guard**
> (C==`forward_progress` → write rung-2 escalation + halt), (6) continue from `Next Action`. Demoted
> the two "primary resumption source" HANDOFF.json claims in `check_incomplete_work` +
> `determine_next_action` to "legacy fallback when no ledger"; extended `<success_criteria>`.
> `commands/gsd/resume-work.md`: one-line `<objective>` pointer (ledger read-first + the §3 steps).
> **LOAD-BEARING ORDER FIX (advisor):** §3's literal order runs the guard (step 4) *before* the
> terminal check (step 5); pulled the terminal + escalation checks AHEAD of the bump+guard — else a
> *finished* project whose completed-count already equals its inherited `forward_progress` would
> false-trip the "zero net progress" guard and halt instead of routing to closeout. (§3 step-order
> clarification, flagged in handoff.) Generation-bump is owned solely by this resume step (W3's flush
> does not bump on resume → no double-count). **`initialize` ROUTING ALSO FIXED (advisor pass 2):**
> its terminal branches said "Proceed to load_state" — for any ledgered project STATE.md exists
> (`state_exists: true`), so a literal executor jumped PAST the new step and skipped the ledger; all
> resume-into-existing branches now route through `ledger_resume` FIRST (new-project stays
> ledger-free), with an explicit "resume-source ordering invariant". Without this the headline "read
> ledger HEAD first" was NOT guaranteed in the common case.
> **FORWARD-PROGRESS GUARD = WIRED-BUT-DEFERRED to W6 (honest flag — NOT faithful to §5):** step 5
> wires the `C == forward_progress` guard but marks it under-specified. Two facts make a naive compare
> unsafe: (a) §5's *write* convention sets `forward_progress := C` **at handoff** (the previous gen's
> *output*), but comparing that to `C` **at takeover** is degenerate — at takeover no work has
> happened, so `C` already equals the inherited count → the guard would false-halt every fresh
> generation that DID inherit progress; (b) the dogfood NEVER exercised this across a real boundary —
> `git log --reverse` shows gen-1 left `forward_progress: 0` (the bump moved to resume per gap (a)),
> and `forward_progress: 2` was written only by gen-2 at completion, so the comparison "passed" by
> staleness, not logic. W4 keeps the (harmless) generation bump, adds a cheap interim `C > 0` gate so
> the initial-`0` snapshot can't false-halt, and **assigns the real reconciliation to W6** (the first
> place the guard runs across generations, in `autonomous.md`; it must redefine §5's snapshot timing
> to compare a generation's *output* vs what it *inherited* at the loop boundary, not at
> resume-takeover). This does NOT block W4: its acceptance is three clauses (resume / git-verify /
> halt-on-escalation), the guard is not in the acceptance, and terminal+escalation short-circuit
> BEFORE the guard so NO traced path touches the defect. **ACCEPTANCE — both branches LIVE-traced against the real dogfood git repo:**
> (terminal) `.planning/LEDGER.md` HEAD read → both done-task SHAs git-verified
> (`9a3c5cb` + `875d5c2` real commits + ancestors of HEAD) → Open Escalations `None.` → `status:
> complete` + terminal Next Action → **ROUTE TO CLOSEOUT** (and confirmed C==forward_progress==2
> *would* false-trip the guard, but the terminal short-circuit correctly prevents it — proving the
> order fix); (escalation/PAUSE) on a **throwaway temp copy** (real dogfood untouched, re-verified
> `status: complete` / `None.` after) injected a non-empty `## Open Escalations` → **PAUSE at step 3,
> bump+guard not reached** — substantiates the "halts on open escalations" acceptance clause.
> Code-fence balance even (26) in resume-project.md. **Structural-only (honest):** the `in_progress`
> idempotent re-run (stash/reset-to-last-clean) and the guard-*trip* (C==forward_progress on an
> *unfinished* project) paths are wired but not exercised by a real run — the dogfood is clean +
> finished, so only read→verify→terminal→closeout and the escalation→PAUSE branch are live-traced; no
> live `/gsd-resume-work` invocation. Backward-compat: ledger-absent → `ledger_resume` no-ops and the
> legacy fallback path runs exactly as before.
- **Files:** `workflows/resume-project.md`, `commands/gsd/resume-work.md`.
- **Change:** read `LEDGER.md` HEAD **first** (before the legacy HANDOFF.json path); run the §3 git-verification algorithm; bump `generation` + run the forward-progress guard; continue from `Next Action`; if `Open Escalations` non-empty → surface + pause. Keep HANDOFF.json as legacy fallback.
- **Acceptance:** `/gsd-resume-work` on a ledgered project resumes from the ledger, git-verifies prior commits, and halts on open escalations. (Protocol already proven by the dogfood; this is the command wiring.)

## W5 — verify-phase: coverage + weakening + gaming + merged verdict  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W5): verify-phase now
> produces a merged eval go/no-go inside the existing VERIFICATION.md. `agents/gsd-verifier.md`
> (the file execute-phase actually spawns) got a new **Step 8b "Eval Contract Verdict"** before
> status determination — (a) coverage gate §3 (REQ⇄eval bijection: uncovered_reqs/orphan_rows →
> BLOCK), (b) weakening detector §4 recomputing `locked_hash` with the **exact §2.1 command** and
> comparing to the stored hash + a verbatim shipped-`<acceptance_criteria>` diff (hash differ w/o
> re-lock, or dropped/skipped/loosened row → BLOCK), (c) gaming detector §4 (`git show <green_sha>
> --stat` per gate row, green-commit sourced from W3's `## LEDGER UPDATE` in SUMMARY.md; row's own
> eval file changed in the green commit → flag; inline-command rows = N/A), (d) Judge (scored now,
> independent) / Human (`{NN}-UAT.md`) gate rows; Code rows green from ledger `passing_eval_ids`
> evidence (NOT re-run → preserves gen≠eval). Its blockers (coverage_hole|weakening|gaming|gate_red)
> feed the Step 9 decision tree; `eval_contract_verdict` frontmatter + a verdict table added to the
> report; success criteria extended. The same section is mirrored **word-for-word** into
> `workflows/verify-phase.md` (new `<step name="eval_contract_verdict">`). **Backward-compat (the
> trap, per advisor):** keyed off the EVAL-CONTRACT.md **file** existing — no contract → whole step
> N/A, verify exactly as before; never gates on `require_contract` (that's plan-phase's already-fired
> gate; double-gating would falsely block every legacy phase). **Retired** `validate-phase` +
> `eval-review`: a `<deprecated>` preamble at the TOP of both `workflows/validate-phase.md` and
> `workflows/eval-review.md` prints an alias notice → `/gsd-verify-work` and **EXITs before the
> auditor spawn** (gsd-nyquist-auditor / gsd-eval-auditor never fire); a backward-compat fallback is
> retained only for legacy no-contract phases; both command `<objective>`s carry a one-line DEPRECATED
> note. ACCEPTANCE: (1) **executed** — the §2.1 `locked_hash` command run on `dogfood/.planning/PLAN.md`
> rows reproduces `637f08b2bab84a805e98f087c9894ff942269b5c1951dc15e035fc6da498a1cd` exactly (MATCH),
> proving author and verify use the identical normalization; (2) coverage-gate **dry trace** — a 2-row
> contract (EC-1→REQ-01, EC-2→REQ-02) with REQ-03 also in scope → `uncovered_reqs=[REQ-03]` → BLOCK
> (gaps_found); bijection logic confirmed in isolation. Code-fence balance even in all 6 edited files.
> **Structural-only (honest):** no live `/gsd-execute-phase`/verifier run — the weakening shipped-row
> diff, gaming git-stat, Judge scoring, and the merged-verdict→Step 9 routing are wired but unexercised
> by a real wave (same honesty class as W1–W4); only the §2.1 hash repro + the coverage bijection are
> executed. **Hash-proof precision:** shipped 8b globs `*-EVAL-CONTRACT.md`; the dogfood's rows live
> in `PLAN.md`, so the dogfood itself takes the **N/A path** — the manual §2.1 run on PLAN.md stands as
> proof of author≡verify *normalization equivalence* (acceptance #1's intent), NOT an end-to-end Step
> 8b execution. **Retire-fallback tension (noted, narrow):** the legacy no-contract fallback in the two
> retired workflows means a `require_contract:false` + no-contract project *could* one-off-run the old
> auditor — slightly dilutes "no longer run independent audits"; left as a documented escape hatch (an
> unconditional EXIT is the maximal-faithfulness alternative). Menu/help pointers to the two retired
> commands (ns-review, help/full, secure-phase, audit-milestone) left for W7 per build-plan scope.
> Human gate-row fix (advisor): 8b.4 now appends a not-yet-PASS Human row to the Step 8
> human_verification list so it routes to `human_needed` (was a silent-pass gap); fixed in both mirrors.
- **Files:** `workflows/verify-phase.md`, `agents/gsd-verifier.md`; deprecate/alias `workflows/validate-phase.md` + `workflows/eval-review.md`.
- **Change:** add the coverage gate (REQ↔eval bijection), weakening detector (diff shipped acceptance_criteria vs `locked_hash` baseline — note: real work, needs the baseline), gaming detector (`git show <green_sha> --stat` shows the eval file changed in the same commit), and Judge/Human row evaluation → one go/no-go verdict. Retire validate-phase + eval-review as separate commands (alias to verify-phase).
- **Acceptance:** verify-phase blocks on uncovered REQ / weakened eval / red gate row; the two retired commands no longer run independent audits.

## W6 — autonomous.md: task-boundary flush + loop-control ladder (Pillar D, lean v1)  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W6): **`workflows/autonomous.md` now applies the v1 loop-control ladder + forward-progress guard at task/phase boundaries, and `references/work-ledger.md §5` is reconciled to unambiguous, provably-terminating semantics.** §5 RECONCILIATION (the load-bearing fix; advisor-decided): the old "compare `C == forward_progress` at takeover" was degenerate because `forward_progress` stored the *previous generation's OUTPUT* → at takeover `C` trivially equals it → false-halts every healthy generation that inherited progress. FIX = change **what `forward_progress` stores, not where the guard runs**: it now stores the **starting baseline = `C` at the moment the current generation took over**, written ONCE per generation at takeover (sole writer = the takeover step; the per-task flush never touches it). The guard, at the NEXT takeover, grades the generation that *just finished* — whose total output is fully realized — by comparing its output `C_now` to its own starting baseline; `C_now == forward_progress` AND work remaining ⇒ that generation added zero tasks ⇒ halt+rung-2 escalate. Seeded `gen=1, fp=0` at creation (no guard, no prior gen); only takeovers guard. This REPLACES W4's interim `C>0` stopgap (which masked a stuck gen-1) — strictly better: stuck gen-1 caught at gen-2 takeover (`C_now==0==fp`). Provably terminating: each gen either advances `C` strictly (bounded by task count → completes) or trips the guard (→ escalates). AUTONOMOUS.MD edits (all additive; every ledger step is a silent no-op when `.planning/LEDGER.md` is absent → legacy unaffected): (1) `<ledger_orchestration>` preamble + field-ownership table — execute-phase (W3) owns per-task records/wave-escalations; autonomous owns `generation`/`forward_progress` (takeover) + loop-control escalations + phase-boundary HEAD; both main-tree (single-writer = subagent-vs-orchestrator); (2) **step 1b takeover guard** runs §5 once per `/gsd-autonomous` invocation (honor pre-existing PAUSE → terminal short-circuit → else guard → bump+snapshot); (3) **step 3c.7 loop-control ladder** derives S1 (≥3 consecutive eval-gate failures) + S2 (lifetime cap 5) purely from each task record's `attempts[]` (no conversation memory) → rung-1 retry-with-different-approach (inline failing eval IDs + last "what was tried"; bounded gap-closure, budget counted in the ledger) while attempts<3, else rung-2 `write_escalation` (§6 Open Escalation + task `status:blocked` + frontmatter `status:blocked` + pause→handle_blocker); (4) `gaps_found` routing made ledger-aware (ladder governs when ledger present; old open-ended user-prompt kept as no-ledger legacy fallback); (5) **phase-boundary HEAD flush** recomputes Tier-1 HEAD each phase boundary; (6) 9 success-criteria lines. Consistency edits: `references/work-ledger.md §3` step-4 wording; `templates/ledger.md` frontmatter comment + lifecycle note (fp written at takeover not handoff); `workflows/resume-project.md` step 5 (removed the `C>0` block, installed the finalized takeover-baseline guard) + step-4 ordering note. ACCEPTANCE (dry-traced, structural-only — no live `/gsd-autonomous` run): (1) **escalation** — unsatisfiable task 04-01-T2 walked through `attempts[]`: pass-1 red→rung1, pass-2 red→rung1, pass-3 red→S1 trips→rung2 writes Open Escalation + pauses; ≤2 rung-1 retries before S1, NO thrash; the awk extractor in step 1b/3c.7 correctly surfaces the full `### ESCALATION — task 04-01-T2 (rung 2)` block from the paused ledger and yields **nothing** on a `None.` ledger (PAUSE fires exactly when an escalation is open); (2) **guard 2-gen** — healthy gen-2 (inherited fp=0, C_now=2) PROCEEDS+sets fp:=2; zero-progress gen-3 (inherited fp=2, C_now=2, work remains) HALTS+escalates — and the old-degeneracy false-halt is shown avoided. Real dogfood ledger re-verified untouched (`status: complete, gen:2, fp:2, None.`); all traces ran in `/tmp`. Code-fence balance even in all edited files (autonomous 120). **Structural-only (honest):** no live `/gsd-autonomous` invocation — the awk extractors, the per-task `attempts[]` HEAD recompute/Write paths, and the multi-generation guard are wired + dry-traced but unexercised by a real autonomous run (the dogfood is a single clean+finished 2-task target — it never ran ≥2 real generations, exactly the gap W4 flagged; W6 reconciles the SEMANTICS + dry-traces them but a genuine multi-gen run remains future work). Consecutive-vs-cumulative red counting for S1 is specified but the ledger's `attempts[]` does not yet carry a per-attempt green-delta tag, so "consecutive" is inferred from `green_eval_count` not rising between attempts — coarse but correct for the all-red unsatisfiable case the acceptance targets.
- **File:** `workflows/autonomous.md`.
- **Change:** flush the ledger at each task/phase boundary; implement **S1** (≥3 consecutive eval-gate failures on a task) + **S2** (lifetime cap 5 attempts) → **rung 1** retry-with-different-approach, then **rung 2** write an Open Escalation + pause. Apply the forward-progress guard per generation. (v2: second-opinion rung, re-plan rung, anti-storm circuit-breaker, signals S3–S8.)
- **INHERITED FROM W4 (must reconcile here):** W4 wired the forward-progress guard into resume but left its `C == forward_progress` comparison **under-specified and deferred to W6** — W6 is the first place the guard runs across real generations. `references/work-ledger.md §5`'s snapshot convention (`forward_progress := C` *at handoff* = the previous generation's *output* count) is degenerate when compared to `C` *at resume-takeover* (at takeover `C` already equals the inherited count → false-halts every fresh generation that inherited progress). Fix §5 + this implementation to compare a generation's *output* against what it *inherited* at the loop boundary (not at takeover), and exercise it across a genuine multi-generation run (the dogfood never did — gen-1 left `forward_progress: 0`, gen-2 wrote `2` only at completion). W4 added an interim `C > 0` gate as a stopgap; remove/replace it once §5 is reconciled.
- **Acceptance:** a deliberately unsatisfiable task escalates to an Open Escalation after 3 attempts and pauses the factory — it does not thrash; the forward-progress guard halts a genuinely zero-progress generation WITHOUT false-halting a healthy one (verified across ≥2 real generations).

## W7 — Register the new assets  — [x] done
> Evidence (2026-06-01, fresh session resumed from LEDGER HEAD `next_action`→W7): the 4 new framework
> files are registered in `.claude/gsd-file-manifest.json` (schema confirmed = `files` map of
> `path` → sha256-of-contents; verified the scheme by re-hashing 3 existing entries → MATCH, then
> inserted the 4 real hashes, alphabetically adjacent to siblings — `references/eval-first.md`,
> `references/work-ledger.md`, `templates/eval-contract.md`, `templates/ledger.md`; `node JSON.parse`
> re-validated, all 4 present). `get-shit-done/templates/README.md` registry now lists `LEDGER.md`
> (root table, template `ledger.md`, produced by `/gsd-execute-phase` sole writer + `/gsd-autonomous`)
> and `NN-EVAL-CONTRACT.md` (phase-subdir table, template `eval-contract.md`, produced by
> `/gsd-spec-phase`/`/gsd-discuss-phase`); also fixed the now-stale `NN-UAT.md` attribution
> (`/gsd-validate-phase` → `/gsd-verify-work`). **BEYOND THE LITERAL FILE LIST (advisor-confirmed, not
> gold-plating):** added `'LEDGER.md'` to `CANONICAL_EXACT` in `get-shit-done/bin/lib/artifacts.cjs` —
> the README documents its own two-step procedure (1. add to CANONICAL_EXACT, 2. add a table row);
> the row alone would leave `LEDGER.md` flagged W019 by `gsd-health` on every run, contradicting W7's
> "framework recognizes the new files" purpose. One-line additive Set edit; `require()` + `isCanonical`
> verified (LEDGER.md→true, EVAL-CONTRACT.md→false since W019 only inspects root). Help: `/gsd-help
> --full` (`help/modes/full.md`) gained `LEDGER.md` in the Files & Structure tree + a new "Eval-First &
> the Work Ledger" subsection (eval contract locked at spec time gates plan/execute/verify; ledger =
> two-tier, execute-phase sole writer, resume-work reads HEAD first + git-verifies). **W5-deferred
> dangling pointers fixed (additive/surgical):** `commands/gsd/ns-review.md` rows → `gsd-verify-work`
> (left `requires:` frontmatter alone — those commands still exist as deprecated aliases, not deleted,
> so not dangling); `help/modes/full.md` rows 591/593 marked *(retired — merged into /gsd-verify-work)*;
> `secure-phase.md` merged the two identical routing lines into one `/gsd-verify-work` line;
> `audit-milestone.md` (4 spots: discovery note, table action, next-up text, success-criteria) repointed
> `/gsd-validate-phase` → `/gsd-verify-work` with "absorbed the retired" notes. **ACCEPTANCE:** (1) manifest
> `JSON.parse` valid + 4 paths present (grep-confirmed); (2) README lists both `LEDGER.md` + `NN-EVAL-CONTRACT.md`;
> (3) help mentions the ledger + eval-first (tree line + dedicated subsection); (4) no live menu/routing
> pointer invokes `validate-phase`/`eval-review` as independent audits — residual grep hits classified:
> the RETIRED preambles themselves, retry-text *inside* the deprecated workflows' legacy-fallback body
> (past the EXIT, only runs when require_contract:false AND no contract), the still-installable command
> `name:` stubs, and the new "absorbed the retired" notes — none are live independent-audit pointers.
> Fences even in all edited md files (README 0, full.md 20, secure-phase 16, audit-milestone 16, ns-review 0).
> **STRUCTURAL-ONLY HONESTY:** the manifest hash scheme was reproduced exactly (proven, not placeholder) so
> these are real checksums; but no live installer/migration run exercised them — I verified the schema +
> hashing match existing entries and that the JSON parses, not that the (unidentified) installer actually
> reads these new keys on a fresh install. No vendored artifact/manifest/health test runner exists in this
> tree to run beyond the direct `JSON.parse`/`require()`/`isCanonical` checks I ran.
- **Files:** `.claude/gsd-file-manifest.json`, `get-shit-done/templates/README.md` (artifact registry), help text.
- **Change:** register `templates/ledger.md`, `templates/eval-contract.md`, `references/work-ledger.md`, `references/eval-first.md`; add `LEDGER.md` + `{NN}-EVAL-CONTRACT.md` to the `.planning/` artifact registry; mention eval-first + the ledger in `/gsd-help`.
- **Acceptance:** the installer/migration recognizes the new files; the README registry lists the two new `.planning/` artifacts.

## W8 — Mobile / full-stack scaffolds  *(SEPARATE DELIVERABLE — not the v1 spine)*
- **Files (new):** `references/mobile-scaffold.md` (React Native + Flutter + native), extend `references/skeleton-template.md` for full-stack vertical slices; per-platform eval hooks (build/run/test gate commands → eval-contract `Code` rows: "app builds", "bundles", "boots in simulator", "e2e smoke passes").
- **Why separate:** large independent surface; the user's core ask is the eval-first + autonomous-handoff spine. Kept out of v1 so it cannot dilute/block the spine. GSD already has `references/ios-scaffold.md` to model the style.
- **Acceptance:** an RN/Flutter phase can author an eval contract whose Code rows are real per-platform build/test commands the executor gates on.

---

## Cross-cutting notes for whoever builds this
- **Dogfood each W task** the way the framework preaches: give it the acceptance above as its eval, and verify it green before moving on.
- **Don't destabilize existing flows.** Each target is a large file; make additive edits, preserve backward-compat (e.g., legacy HANDOFF.json, projects without a ledger).
- **Keep the discipline:** modify/unify/retire before add. W5 *retires* two commands — that's the point.
- **The meta-dogfood is live:** this very framework-build is tracked in `design/LEDGER.md`. A fresh session continuing W1+ is itself proof the handoff/ledger model works at real scale.
