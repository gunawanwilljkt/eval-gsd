# eval-gsd

**GSD (Get Shit Done)** — a spec-driven development framework for Claude Code — plus an
additive **eval-first + context-resilient** layer. Same install, same 67 commands; the
eval layer only switches on when you opt in (author an eval contract / set a config flag).

> From a raw idea to a merged PR: every phase is a vertical slice that's discussed, planned,
> executed and verified by specialized agents — and it can't pass until its pre-committed
> evals go green.

## Install

GSD installs as Claude Code `/gsd-*` slash commands. You need
[Node.js](https://nodejs.org) (for `npx`) and [Claude Code](https://claude.com/claude-code).

```bash
# Into the current project (recommended) — adds the .claude/ commands here
npx -y @opengsd/gsd-core@latest --claude --local

# Or install once for every project on your machine
npx -y @opengsd/gsd-core@latest --claude --global
```

This installs **v1.2.0**. Update any time from inside Claude Code with `/gsd-update`, or just
re-run the command above. GSD also targets other AI runtimes — swap `--claude` for the
matching flag (e.g. `--codex`, `--gemini`).

## Getting started

Open Claude Code in your project and drive the loop with slash commands:

```text
/gsd-new-project        # scope it: questions -> requirements -> roadmap
/gsd-discuss-phase 1    # lock the decisions for phase 1
/gsd-plan-phase 1       # planner <-> checker -> executable tasks
/gsd-execute-phase 1    # parallel waves + hard gates + verify
/gsd-ship 1 --review    # open a PR, with a code review
```

- **New here?** `/gsd-help` lists all 67 commands.
- **Lost mid-project?** `/gsd-progress` reads your state and tells you exactly what's next.
- **Want it hands-free?** `/gsd-autonomous` runs every remaining phase, pausing only for a
  blocked gate or a real decision.

> Tip: the [`presentation/`](presentation/) deck walks the whole loop end to end, plus two
> complete example builds (a SaaS app and a payment gateway).

## What's in here

| Path | What it is |
|------|------------|
| [`presentation/`](presentation/) | A 58-slide deck + landing page explaining how GSD works and how to use it, with two end-to-end examples (a SaaS app and a payment gateway). Dark / light / zero-fill-print themes + PDF. **Start here.** |
| `.claude/` | The GSD framework itself — workflows, agents, references, templates, hooks, and the `get-shit-done` toolkit (v1.2.0). |
| `design/` | Design notes on the framework (landscape, architecture, dogfood proof, build plan, original-GSD vs eval-gsd). |
| `dogfood/`, `gsd-livetest/`, `webrtc-video-call/` | Example projects built with GSD, each with a real `.planning/` artifact trail. |
| `.planning/` | Planning state for this workspace. |

## The presentation

The deck explains the framework end to end and is the best on-ramp:

- **[Landing page](presentation/index.html)** — overview + links to every version
- **[Dark deck](presentation/gsd-presentation-dark.html)** · **[Light deck](presentation/gsd-presentation-light.html)** · **[Print deck](presentation/gsd-presentation-print.html)**
- **[Print PDF (58 pages)](presentation/gsd-presentation-print.pdf)**

All decks are self-contained HTML — open them directly, no server or internet needed.

## The core loop

```
new-project  →  for each phase: discuss → plan → execute → verify  →  ship
```

Eval-first contracts gate every phase, a git-verified work ledger makes a dropped session a
non-event, and 20+ specialized agents run in dependency-ordered parallel waves.

---

*Get Shit Done · spec-driven development for Claude Code · from idea to merged PR, with proof at every gate.*
