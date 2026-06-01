---
name: gsd-eval-review
description: Audit an executed AI phase's evaluation coverage and produce an EVAL-REVIEW.md remediation plan.
argument-hint: "[phase number]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
requires: [phase]
---
<objective>
**DEPRECATED (eval-first / W5):** retired in favor of `/gsd-verify-work` — AI eval coverage is now
part of verify-phase's merged Eval Contract Verdict (AI-SPEC §5 rows fold into the eval contract;
Judge rows carry the AI-quality dimensions). This command exits with an alias notice; the workflow
only runs as a backward-compat fallback for legacy AI-SPEC-without-contract phases. See
`references/eval-first.md` §5.

Conduct a retroactive evaluation coverage audit of a completed AI phase.
Checks whether the evaluation strategy from AI-SPEC.md was implemented.
Produces EVAL-REVIEW.md with score, verdict, gaps, and remediation plan.
</objective>

<execution_context>
@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/workflows/eval-review.md
@/Users/gunawanwilljkt/harness/eval-gsd/.claude/get-shit-done/references/ai-evals.md
</execution_context>

<context>
Phase: $ARGUMENTS — optional, defaults to last completed phase.
</context>

<process>
Execute end-to-end.
Preserve all workflow gates.
</process>
