# Original GSD vs. eval-gsd — what changed & how to use both

> **The one thing to understand first:** eval-gsd is **original GSD v1.2.0 + an additive
> "eval-first + context-resilient" layer**. It is the *same* install, the *same* 67 commands.
> You don't pick one or the other at runtime — the new behavior only switches ON when you opt
> in (author an eval contract / set a config flag). With the new features off, it behaves
> *exactly* like original GSD. So "using both" = one framework, two modes, chosen by config.

---

## 1. The 5 things eval-gsd ADDS

| # | New capability | New asset(s) | What it does |
|---|----------------|--------------|--------------|
| A | **Eval-first contracts** | `templates/eval-contract.md`, `references/eval-first.md`, the per-phase `{NN}-EVAL-CONTRACT.md` | Every phase gets a **locked eval contract** authored at spec time; its deterministic rows become the executor's gate. Red→green on evals *is* progress. |
| B | **The Work Ledger** | `templates/ledger.md`, `references/work-ledger.md`, the per-project `.planning/LEDGER.md` | An always-warm, git-verified, sub-task-granular task ledger. The single thing a fresh session reads to resume. Subsumes the old manual `HANDOFF.json`. |
| C | **Autonomous context-resilient handoff** | upgraded `hooks/gsd-context-monitor.js` + `continuation.*` config | At context-WARNING it tells the agent to checkpoint the ledger (handoff becomes a non-event). Optional auto-spawn policy. |
| D | **Loop-control / escalation** | new steps in `workflows/autonomous.md` | The autonomous loop detects non-convergence (consecutive eval-fails / attempt cap) and **escalates to a human instead of thrashing**. |
| E | **Mobile / full-stack scaffolds** | `references/mobile-scaffold.md` | Per-platform **eval-hook tables** (RN/Flutter/native iOS+Android, full-stack slices) so mobile phases can author real Code-gated eval contracts. |

It also **RETIRES** two commands: `validate-phase` and `eval-review` are merged into one
go/no-go verdict inside `verify-phase` (they now alias to `/gsd-verify-work`).

---

## 2. Which commands behave differently

Same command names; behavior is a *superset* (the extra steps only fire when their inputs exist).

| Command | Original GSD | eval-gsd (when eval-first is on) |
|---------|--------------|----------------------------------|
| `/gsd-spec-phase` | clarifies WHAT a phase delivers | **+ authors & LOCKS** `{NN}-EVAL-CONTRACT.md` (coverage gate + `locked_hash`) |
| `/gsd-plan-phase` | breaks the phase into tasks/waves | **+ §1.6 gate**: blocks if no locked contract; **planner emits** each `gate`+`Code` contract row as a task `<acceptance_criteria>` (+ `<eval_rows>`) |
| `/gsd-execute-phase` | wave exec + atomic commits | **+ orchestrator is the SOLE writer of `.planning/LEDGER.md`** (executors emit `## LEDGER UPDATE`); per-task acceptance gate is a hard red→green gate |
| `/gsd-verify-work` / verify-phase | UAT + goal-backward checks | **+ merged eval verdict**: coverage (REQ⇄eval) + weakening (hash recompute) + gaming (same-commit eval edit) + Judge/Human routing |
| `/gsd-resume-work` | reads STATE.md / `HANDOFF.json` | **reads `LEDGER.md` HEAD first**, git-verifies each "done" commit, halts on open escalations, routes terminal→closeout |
| `/gsd-autonomous` | chains phases | **+ loop-control**: forward-progress guard + S1/S2 → retry → Open-Escalation-and-pause |
| `/gsd-validate-phase`, `/gsd-eval-review` | two separate audits | **RETIRED** → alias to the merged verify verdict |
| everything else (67 cmds) | unchanged | unchanged |

---

## 3. New config knobs (`.planning/config.json`)

```jsonc
"eval_first": {
  "require_contract": true,      // every phase needs a locked contract before plan-phase
  "coverage_gate": true,         // enforce REQ ⇄ eval bijection
  "weakening_detector": true     // verify recomputes locked_hash, flags weakened evals
},
"continuation": {
  "policy": "warm-ledger",       // manual | warm-ledger | autonomous
  "checkpoint_at": "task-boundary",
  "trigger_remaining_pct": 35
}
```

Both blocks are settable via the supported command (`gsd-tools query config-set …`) — that
wiring was a bug we found+fixed during validation.

---

## 4. How to use BOTH (it's a config choice, not two installs)

**Mode 1 — "classic GSD" (eval-first OFF):**
- Set `eval_first.require_contract: false` in `.planning/config.json`.
- Then spec→plan→execute→verify behave **exactly like original GSD**: the §1.6 gate no-ops, no
  contract is authored, verify's eval-verdict is N/A, the ledger steps no-op. Use this for
  quick/throwaway work or projects where you don't want eval gating.

**Mode 2 — "eval-first" (default, ON):**
- Leave `eval_first.require_contract: true`.
- Author requirements, run `/gsd-spec-phase` → it builds and locks the eval contract → the
  planner turns its Code rows into the executor's gate → **the phase can't pass until its evals
  are green** → verify confirms nothing was weakened or gamed. Use this when "did the code
  actually do what the spec said?" must be *proven*, not assumed.

**Mixing:** it's effectively per-phase. A phase with a locked contract is gated; a phase with
**no** `{NN}-EVAL-CONTRACT.md` falls back to classic behavior automatically. So you can adopt
eval-first incrementally.

---

## 5. Backward-compatibility guarantees (verified, not assumed)

Every new behavior is additive and **no-ops when its trigger is absent**:
- `plan-phase` §1.6 gate → no-op when `eval_first.require_contract` is absent/false.
- `verify-phase` §8b eval verdict → **N/A** when there's no `{NN}-EVAL-CONTRACT.md` file.
- ledger steps in execute/resume → no-op when there's no `.planning/LEDGER.md`.
- `HANDOFF.json` + `.continue-here.md` → still work as the **legacy** resume fallback.
- All original commands/agents present and unchanged in behavior absent the new artifacts.

This was confirmed by (a) the WebRTC app build, (b) a live `/gsd-*` cycle on a trivial target,
and (c) spawning the real `gsd-planner`/`gsd-executor`/`gsd-verifier` agents and watching them
comply. See `design/LEDGER.md` decision log for the evidence trail.

---

## 6. TL;DR
- **Same framework, one install.** eval-gsd = GSD + (eval contracts · work ledger · resilient
  handoff · loop-control · mobile scaffolds).
- **Default ON** (`eval_first.require_contract: true`) gives you the new eval-gated,
  context-resilient workflow.
- **Flip one flag OFF** and it's classic GSD again.
- **Two commands retired** (`validate-phase`, `eval-review` → merged into verify).
- **Nothing else you knew about GSD changed.**
