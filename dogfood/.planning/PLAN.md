---
phase: 01-calc
plan: 01
objective: "Provide a tiny calc module: add and subtract, each proven by a deterministic eval."
---

# Plan 01 — calc module

Objective (intent): a `calc` module exposing `add(a,b)` and `sub(a,b)`, each confirmed by a
deterministic eval-contract row. REQ traceability: REQ-01 (addition), REQ-02 (subtraction).

## Eval Contract (authored at spec time, locked)

| id | objective_ref | req_ref | behavior | measurement | command | severity |
|----|---------------|---------|----------|-------------|---------|----------|
| EC-1 | calc | REQ-01 | `add(2,3) == 5` | Code | `python3 -c "import sys;sys.path.insert(0,'src');from calc import add;assert add(2,3)==5;print('EC-1 PASS')"` | gate |
| EC-2 | calc | REQ-02 | `sub(5,3) == 2` | Code | `python3 -c "import sys;sys.path.insert(0,'src');from calc import sub;assert sub(5,3)==2;print('EC-2 PASS')"` | gate |

## Tasks

### T1 — implement add()  (eval_rows: EC-1, req: REQ-01)
- Create/extend `src/calc.py` with `add(a, b)` returning the sum.
- acceptance_criteria (HARD GATE — run it, must exit 0):
  `python3 -c "import sys;sys.path.insert(0,'src');from calc import add;assert add(2,3)==5;print('EC-1 PASS')"`
- Commit atomically.

### T2 — implement sub()  (eval_rows: EC-2, req: REQ-02)
- Extend `src/calc.py` with `sub(a, b)` returning the difference.
- acceptance_criteria (HARD GATE — run it, must exit 0):
  `python3 -c "import sys;sys.path.insert(0,'src');from calc import sub;assert sub(5,3)==2;print('EC-2 PASS')"`
- Commit atomically.
