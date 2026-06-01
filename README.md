# eval-gsd

**GSD (Get Shit Done)** — a spec-driven development framework for Claude Code — plus an
additive **eval-first + context-resilient** layer. Same install, same 67 commands; the
eval layer only switches on when you opt in (author an eval contract / set a config flag).

> From a raw idea to a merged PR: every phase is a vertical slice that's discussed, planned,
> executed and verified by specialized agents — and it can't pass until its pre-committed
> evals go green.

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
