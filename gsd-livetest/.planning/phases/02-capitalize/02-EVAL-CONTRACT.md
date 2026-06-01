---
eval_contract_version: '1.0'
phase: '02-capitalize'
status: locked
locked_hash: 'bd7b28f2de6c8b63434356654ffa546da3105c33c11b13b0a851eb85a61166a6'
locked_at: '2026-06-01'
coverage:
  requirements: [REQ-03, REQ-04]
  rows_total: 3
  uncovered_reqs: []
  orphan_rows: []
---

# Phase 02 — Eval Contract (capitalize)

Intent: `capitalize(text)` upper-cases the first char, lower-cases the rest, empty-safe.

Mixed measurement on purpose: EC-3 and EC-4 are deterministic `Code` gates (the planner MUST
emit these as task `<acceptance_criteria>`); EC-5 is a `Human` row (the planner MUST NOT emit it
as a per-task gate — it is carried to verify-phase / UAT).

## Rows

| id | objective_ref | req_ref | behavior | measurement | command_or_rubric | sample_rate | severity |
|----|---------------|---------|----------|-------------|-------------------|-------------|----------|
| EC-3 | cap | REQ-03 | capitalize('hELLO') returns 'Hello' (first upper, rest lower) | Code | node -e "import('./src/capitalize.mjs').then(m=>process.exit(m.capitalize('hELLO')==='Hello'?0:1)).catch(()=>process.exit(1))" | per-task | gate |
| EC-4 | cap | REQ-04 | capitalize('') returns '' (empty-safe, no crash) | Code | node -e "import('./src/capitalize.mjs').then(m=>process.exit(m.capitalize('')===''?0:1)).catch(()=>process.exit(1))" | per-task | gate |
| EC-5 | cap | REQ-03 | the capitalized output reads naturally to a person | Human | UAT U-1: a reviewer confirms the output reads naturally | pre-verify | gate |

## Human / UAT rows
- EC-5 — carried to `02-UAT.md` at verify-work. Must NOT be emitted as a per-task Code gate.
