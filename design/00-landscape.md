# 00 — Landscape: What GSD Already Is

> **Purpose of this doc.** Before designing anything, I mapped the existing GSD
> ("get-shit-done") framework that lives in `.claude/`. This is the durable record of
> *what is already here* so that (a) we build on it instead of reinventing it, and
> (b) any fresh agent picking up this work starts from facts, not guesses.
>
> Method: 4 parallel read-only exploration agents, each mapping one subsystem
> (lifecycle/state, evals, context/handoff, authoring conventions). Findings below are
> their synthesis with exact file paths.

---

## 0. TL;DR

GSD is a **mature spec-driven development (SDD) framework, v1.2.0**. It is *not* a blank
slate. It already implements:

- A complete lifecycle: `new-project → roadmap → discuss-phase → plan-phase → execute-phase → verify-work → verify-phase → complete-milestone`
- A durable `.planning/` state model (PROJECT/ROADMAP/STATE/REQUIREMENTS + per-phase artifacts)
- Wave-based **parallel execution** with git-worktree isolation and subagent dispatch
- A real **evaluation subsystem**: eval-planner, eval-auditor, nyquist-auditor, AI-SPEC.md, a 10-dimension eval taxonomy, EVAL-REVIEW.md, VALIDATION.md
- **Context monitoring** (a PostToolUse hook with 35%/25% thresholds) and **manual** pause/resume handoff (HANDOFF.json + `.continue-here.md`)
- An **autonomous mode** that chains phases via fresh-context subagents
- Clear authoring conventions for commands, workflows, agents, templates, hooks

**The user's goal is therefore an *evolution*, not a rebuild.** The three things they
asked for map onto three precise structural gaps (see §5).

---

## 1. The Lifecycle & State Model

### Lifecycle stages → artifacts produced

```
new-project        → PROJECT.md, ROADMAP.md, REQUIREMENTS.md, STATE.md
  ↓
discuss-phase      → {NN}-CONTEXT.md        (locked decisions, gray areas)
  ↓
[ai-integration]   → {NN}-AI-SPEC.md        (OPTIONAL — eval strategy, AI features)
  ↓
plan-phase         → {NN}-{MM}-PLAN.md      (tasks, depends_on, waves, requirements)
  ↓
execute-phase      → {NN}-{MM}-SUMMARY.md   (wave-based parallel exec, commits)
  ↓
verify-work        → {NN}-UAT.md            (manual user-acceptance test results)
  ↓
verify-phase       → {NN}-VERIFICATION.md   (gate: Complete | Needs Review)
  ↓
complete-milestone → archive to .planning/milestones/vX.Y-*
```

### `.planning/` directory layout (reconstructed)

```
.planning/
├── PROJECT.md            # identity, core value, constraints
├── ROADMAP.md            # phase list, success criteria, dependencies
├── STATE.md              # active phase/plan, progress %, velocity, last activity
├── REQUIREMENTS.md       # functional reqs table + traceability (REQ-NN)
├── BACKLOG.md            # deferred work
├── LEARNINGS.md          # phase retrospectives
├── config.json           # branching, worktrees, commit_docs, language
├── phases/
│   └── NN-name/
│       ├── NN-CONTEXT.md        # decisions (discuss-phase)
│       ├── NN-MM-PLAN.md        # tasks + waves (plan-phase)
│       ├── NN-MM-SUMMARY.md     # what shipped (execute-phase) — existence = "done"
│       ├── NN-RESEARCH.md       # optional technical research
│       ├── NN-VALIDATION.md     # Nyquist verification architecture
│       ├── NN-UAT.md            # user-acceptance test results
│       ├── NN-VERIFICATION.md   # phase gate status
│       ├── NN-AI-SPEC.md        # eval strategy (if AI phase)
│       └── NN-{UI,SECURITY,PATTERNS,DEBUG}-*.md
└── milestones/vX.Y-*/    # archived roadmaps/requirements/phases
```

### How task lists persist across sessions

- **STATE.md frontmatter** carries `status`, progress counters, current phase/plan, last activity.
- **PLAN.md frontmatter** is the task list: `wave`, `depends_on: [01-01,...]`, `files_modified`, `requirements: [REQ-01]`, `autonomous: true/false`.
- **Completion signal** is *coarse*: a plan is "done" when its `SUMMARY.md` exists. There is **no sub-task-granular, continuously-updated ledger** — interruption *inside* a plan loses the fine-grained position.
- **Resume protocol**: read STATE.md → ROADMAP.md → CONTEXT.md → scan for plans missing SUMMARY.md → continue.

### Parallelization (execute-phase)

Topological sort of `depends_on` → **waves**. Wave-N tasks run in parallel via
`Agent(subagent_type="gsd-executor", isolation="worktree")`. Each executor commits, writes
SUMMARY.md, returns status. Orchestrator advances waves.

### Key files to read
- `.claude/get-shit-done/templates/README.md` — registry of all artifacts
- `.claude/get-shit-done/workflows/new-project.md`
- `.claude/get-shit-done/workflows/execute-phase.md`
- `.claude/get-shit-done/workflows/plan-phase.md`
- `.claude/get-shit-done/workflows/discuss-phase.md`

---

## 2. The Evaluation Subsystem (already substantial)

### Eval assets inventory

| Asset | Role | In → Out |
|---|---|---|
| `gsd-eval-planner` (agent) | Designs eval strategy **before** impl | phase goal + domain → AI-SPEC §5–7 |
| `gsd-eval-auditor` (agent) | Audits eval coverage **after** impl | AI-SPEC + SUMMARYs → EVAL-REVIEW.md |
| `gsd-nyquist-auditor` (agent) | Fills behavioral-test gaps | PLAN + VALIDATION → test files |
| `gsd-domain-researcher` (agent) | Domain eval criteria, failure modes | vertical → AI-SPEC §1b |
| `gsd-ai-researcher` (agent) | Framework best practices | framework → AI-SPEC §3–4 |
| `/gsd-ai-integration-phase` | Orchestrates eval design at spec time | → AI-SPEC.md |
| `/gsd-eval-review` | Retroactive eval audit | → EVAL-REVIEW.md |
| `/gsd-validate-phase` | Nyquist behavioral validation | → VALIDATION.md + tests |
| `/gsd-verify-work` | Manual UAT | → UAT.md |
| `/gsd-add-tests` | Retroactive test generation | → test files |

### The eval taxonomy (from `references/ai-evals.md`)

10 pre-deployment dimensions: factual accuracy, context faithfulness, hallucination,
escalation accuracy, policy compliance, tone/style, output-structure validity, task
completion, tool-use correctness, safety. Plus 5 production-monitoring dimensions.

**Rubric format** (AI-SPEC §5):
```
PASS: {acceptable behavior in domain language}
FAIL: {unacceptable behavior in domain language}
Measurement: Code | LLM Judge | Human
Priority: Critical | High | Medium
```
Reference dataset guideline: 10–20 high-quality examples. Code-based checks preferred
first; LLM-judge for subjectivity (needs calibration); human as gold standard.

### Where evals happen today
**Designed early, run late, never gate.** AI-SPEC (incl. eval strategy) is *optional*,
inserted between discuss and plan. The **executor never reads §5–7**, so no tracing, no
reference-dataset build, no eval runs during development. Audits (EVAL-REVIEW, VALIDATION,
UAT) run **only after** execution and are **advisory, not blocking**.

### Key files
- `.claude/get-shit-done/references/ai-evals.md`
- `.claude/agents/gsd-eval-planner.md`, `gsd-eval-auditor.md`
- `.claude/get-shit-done/templates/AI-SPEC.md`
- `.claude/get-shit-done/workflows/ai-integration-phase.md`

---

## 3. Context Management & Handoff (monitors, but does not act)

### Measurement (`.claude/hooks/gsd-context-monitor.js`)
- A statusline hook writes context metrics to `/tmp/claude-ctx-{session_id}.json` after each tool use.
- The monitor (PostToolUse) reads `remaining_percentage` and evaluates thresholds:
  - `WARNING_THRESHOLD = 35` (≤35% remaining → advisory)
  - `CRITICAL_THRESHOLD = 25` (≤25% remaining → critical advisory)
  - `DEBOUNCE_CALLS = 5` (max 1 message per 5 tool uses)

### What happens at high context — **the critical finding**
- **WARNING (35%)**: injects an advisory string ("avoid starting new complex work"). No action.
- **CRITICAL (25%)**: fire-and-forget `state record-session --stopped-at "context exhaustion"`
  writes a *breadcrumb* to STATE.md, then injects a message that **explicitly tells the
  agent NOT to write handoff files** and to *"inform the user so they can run
  `/gsd-pause-work`."*

➡️ **There is no autonomous detect → checkpoint → spawn-fresh-session loop.** Handoff is
always human-triggered. This is exactly the user's central ask.

### Manual handoff artifacts (`/gsd-pause-work`)
- `.planning/HANDOFF.json` — structured: completed_tasks, remaining_tasks, blockers,
  decisions, uncommitted_files, `next_action`, `context_notes`.
- `.planning/.continue-here.md` — human narrative + blocking constraints w/ checkboxes that
  resume/execute workflows must parse.
- `/gsd-resume-work` reads HANDOFF.json first, deletes it after resuming (one-shot).

### Autonomous mode (`workflows/autonomous.md`)
Chains phases in a **single orchestrator context**, dispatching plan/execute to
**fresh-context subagents**. Survives *within-phase* context exhaustion (subagents are
fresh) but the **main orchestrator context can still run out mid-chain** with no recovery.

### Key files
- `.claude/hooks/gsd-context-monitor.js` ← most important
- `.claude/get-shit-done/workflows/pause-work.md`
- `.claude/get-shit-done/workflows/resume-project.md`
- `.claude/get-shit-done/workflows/autonomous.md`
- `.claude/get-shit-done/references/context-budget.md`

---

## 4. Authoring Conventions (how to extend GSD)

- **Command**: `.claude/commands/gsd/{name}.md`. Frontmatter `name: gsd-{slug}`,
  `description`, `argument-hint`, `allowed-tools`. Body: `<objective>`,
  `<execution_context>` (@-paths to workflow), `<process>`. Thin shell → points at a workflow.
- **Workflow**: `.claude/get-shit-done/workflows/{name}.md` (or a folder with steps/modes).
  Body: `<purpose>`, `<required_reading>` (@-paths), `<available_agent_types>`, `<process>`
  with `<step name="...">`. Workflows orchestrate agents and wait for ALL-CAPS completion
  markers (`## PLANNING COMPLETE`).
- **Agent**: `.claude/agents/gsd-{slug}.md`. Frontmatter `name`, `description`, `tools`,
  `color`, `effort`. Body: `<role>`, `<required_reading>`, then specialised sections. Ends
  with a structured completion marker.
- **Template**: `.claude/get-shit-done/templates/{name}.md`. Placeholders `{N}`,
  `{phase_name}`, `{variable}`, `[optional]`.
- **Hook**: `.claude/hooks/gsd-{purpose}.{js,sh}`. Reads JSON on stdin; allow = exit 0;
  block = exit 2 + `{"decision":"block","reason":...}` on stdout; warn = stderr + exit 0.
  Shared libs in `.claude/hooks/lib/`.
- **Naming**: command `/gsd-{kebab}`; agents/hooks `gsd-{kebab}`.

### Mobile / full-stack support today
- iOS: `references/ios-scaffold.md` (XcodeGen patterns).
- Full-stack vertical slice: `references/skeleton-template.md` (MVP "walking skeleton").
- **No React Native / Flutter / Android scaffolds.** Mobile coverage is thin.

### Canonical files to copy when authoring
- command → `commands/gsd/plan-phase.md` (complex) or `fast.md` (simple)
- workflow → `workflows/plan-phase.md`
- agent → `agents/gsd-planner.md` or `gsd-debugger.md`
- template → `templates/context.md` or `templates/AI-SPEC.md`
- hook → `hooks/gsd-validate-commit.sh` + `hooks/lib/git-cmd.js`

---

## 5. The Three Gaps (this is the whole job)

The user's goal decomposes into exactly three structural gaps in today's GSD:

### Gap A — Evals are designed early but run late and never gate
- AI-SPEC eval strategy is **optional**, **AI-only-framed**, **not consumed by the
  executor**, and audits are **advisory**. The user wants evals to be:
  - **First-class & mandatory** (every phase has an eval contract).
  - **Spec-conformance evals for *all* code**, not just AI-quality evals — "confirm it
    follows specs and intention," which is broader than the LLM-judge taxonomy.
  - **Run alongside development and used as gates** (red→green is the progress signal).

### Gap B — No autonomous context-resilient handoff
- The monitor only *advises*; handoff is *manual*; the autonomous orchestrator can die
  mid-chain. The user wants: **autonomously detect context rot → checkpoint → spawn a
  fresh session that resumes seamlessly**, before quality degrades.

### Gap C — Task list isn't granular/continuous enough for seamless pickup
- State is coarse (plan-level via SUMMARY.md existence). The user wants a **continuously
  updated, durable, sub-task-granular work ledger** any fresh agent reads first to know
  exactly where to continue.

### And the meta-vision
- **Software factory**: wire A+B+C into a self-running loop —
  `objective → spec(+eval contract) → plan → execute(eval-gated) → verify → handoff-and-continue`
  — that survives unlimited context resets and runs to completion autonomously.

---

*Next: `01-thesis.md` — the proposed architecture, pressure-tested by the advisor and by
peer variant agents before any code is written.*
