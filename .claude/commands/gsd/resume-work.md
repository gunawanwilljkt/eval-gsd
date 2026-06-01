---
name: gsd-resume-work
description: Resume work from previous session with full context restoration
allowed-tools:
  - Read
  - Bash
  - Write
  - AskUserQuestion
  - SlashCommand
---

<objective>
Restore complete project context and resume work seamlessly from previous session.

Routes to the resume-project workflow which handles:

- **Work Ledger (`.planning/LEDGER.md`) read FIRST when present** — the git-verified §3
  resume algorithm (read Tier-1 HEAD → git-verify done commits → PAUSE on open escalations →
  closeout on terminal → else bump generation + forward-progress guard + resume from Next Action)
- STATE.md loading (or reconstruction if missing)
- Legacy fallback when no ledger: HANDOFF.json / .continue-here checkpoint detection
- Incomplete work detection (PLAN without SUMMARY)
- Status presentation
- Context-aware next action routing
  </objective>

<execution_context>
@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/workflows/resume-project.md
</execution_context>

<process>
Execute end-to-end.
</process>
