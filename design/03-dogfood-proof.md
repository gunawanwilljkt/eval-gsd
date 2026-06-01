# 03 — Dogfood Proof: the handoff seam actually runs

> The advisor's #1 risk was "a beautiful markdown framework that's never executed." So before
> building the rest of the spine, we proved the keystone seam on a real, controlled target.
> This is the evidence. It is also the single most important result so far.

## The experiment

A throwaway git repo at `dogfood/` with a trivial 2-task target (a `calc` module: `add`,
then `sub`), each task gated by a deterministic **eval-contract row** (EC-1, EC-2) — a real
command that must exit 0.

1. **Session 1 (me, as orchestrator):** authored the eval contract at spec time (`PLAN.md`),
   implemented T1 (`add`), ran the EC-1 **hard gate** (`EC-1 PASS`, exit 0), committed T1
   (`9a3c5cb`), and **flushed the warm ledger** (`LEDGER.md`) marking T1 done / T2 next, then
   committed the ledger (`3b2ba91`). This is the exact state a context-pressure handoff leaves.
2. **Forced handoff:** stopped. Spawned a **genuinely fresh-context agent** whose *entire*
   instruction was "resume from the ledger" — it was told **nothing** about what T2 was or how
   to do it. All task knowledge had to come from reading `LEDGER.md` + the protocol.

## The result — PASS

The fresh agent, with zero prior context:
- read the **Tier-1 HEAD** and learned the Next Action;
- **git-verified** the ledger's claim that T1 was done at `9a3c5cb` *before trusting it*
  (the protocol's "git is ground truth" step — it actually did it);
- executed the Next Action: implemented `sub`, ran the **EC-2 hard gate** (`EC-2 PASS`,
  exit 0), committed T2 (`875d5c2`);
- **flushed the ledger** as sole writer: T2 done + evidence, recomputed HEAD, bumped
  `generation` 1→2, status → complete, appended the Decision Log, committed.

➡️ **A fresh session resumed an interrupted, eval-gated build from a durable artifact alone
and finished it correctly.** That is exactly the user's ask: "autonomously hand off to
another session that starts fresh and picks up where it left off," with evals confirming
each step. Proven, not asserted.

## What the dogfood caught (the payoff) — 4 spec gaps, now fixed

The fresh agent's honesty check surfaced ambiguities a fresh session shouldn't have to guess.
All four are now fixed in `references/work-ledger.md`:

| # | Gap found | Fix applied |
|---|---|---|
| a | Generation-bump wasn't owned anywhere the resumer would reliably see it | Resume algorithm §3 now **mandates** the bump as step 4, explicitly owned by the protocol (not the ledger HEAD) |
| b | The two-commit convention (work commit, then separate ledger flush) was only inferable from git history | §2 now states the **commit convention** explicitly (and ties it to the §7 gaming check) |
| c | Terminal state (what Next Action becomes after the *final* task) undefined | §3 step 5 now defines the **terminal-state handoff** to closeout |
| d | `forward_progress` snapshot timing genuinely ambiguous (the anti-respawn guard) | §5 now **pins the timing**: snapshot at handoff, compare this generation's progress vs. what it inherited → provably terminating |

## Why this matters for the rest of the build

The riskiest, most novel part of the whole framework — *autonomous context-resilient
continuation* — now has a working, tested seam. Everything else (eval-contract authoring,
the context-monitor hook that *triggers* the handoff automatically, loop-control) builds on a
foundation we've watched run. The remaining work is wiring around a proven core.

*Dogfood artifacts live in `dogfood/` (a self-contained git repo). Safe to delete; kept as
runnable evidence.*
