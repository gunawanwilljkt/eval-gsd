---
eval_contract_version: '1.0'
phase: '01-slugify'
status: locked
locked_hash: '529139f9198cdf6d056d498f65c1dfd961f8edcbc5b65ed4215c0fc02f0ec36c'
locked_at: '2026-06-01'
coverage:
  requirements: [REQ-01, REQ-02]
  rows_total: 2
  uncovered_reqs: []
  orphan_rows: []
---

# Phase 01 — Eval Contract

Intent (one line, from the objective): "A user can turn any text into a clean URL slug."

## Rows

Each row is one provable claim. `objective_ref → req_ref` makes every eval traceable back to
intent. `measurement` picks the cheapest honest evaluator. `command_or_rubric` is runnable
(Code) or a scored rubric (Judge/Human). `severity: gate` rows BLOCK; `warn` rows inform.

| id | objective_ref | req_ref | behavior (acceptance altitude) | measurement | command_or_rubric | severity |
|----|---------------|---------|--------------------------------|-------------|-------------------|----------|
| EC-1 | slugify | REQ-01 | `slugify("Hello World") === "hello-world"` | Code | `node --input-type=module -e "import {slugify} from './src/slugify.mjs';if(slugify('Hello World')!=='hello-world')process.exit(1);console.log('EC-1 PASS')"` | gate |
| EC-2 | slugify | REQ-02 | `slugify("  A__B--C!  ") === "a-b-c"` | Code | `node --input-type=module -e "import {slugify} from './src/slugify.mjs';if(slugify('  A__B--C!  ')!=='a-b-c')process.exit(1);console.log('EC-2 PASS')"` | gate |
