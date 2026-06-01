# Roadmap: slugify-lib

## Overview

One phase: implement `slugify(text)` and prove it against the two requirements.

## Phases

- [x] **Phase 1: Slugify** - Implement the slugify function with eval-first proof.
- [ ] **Phase 2: Capitalize** - Implement `capitalize(text)` with eval-first proof.

## Phase Details

### Phase 1: Slugify
**Goal**: A working `slugify(text)` ESM function that satisfies REQ-01 and REQ-02.
**Depends on**: Nothing (first phase)
**Requirements**: [REQ-01, REQ-02]
**Success Criteria** (what must be TRUE):
  1. `slugify("Hello World")` returns `"hello-world"`.
  2. `slugify("  A__B--C!  ")` returns `"a-b-c"`.
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Implement slugify and wire eval-contract gates.

### Phase 2: Capitalize
**Goal**: A working `capitalize(text)` ESM function that satisfies REQ-03 and REQ-04.
**Depends on**: Nothing (independent of Phase 1)
**Requirements**: [REQ-03, REQ-04]
**Success Criteria** (what must be TRUE):
  1. `capitalize("hELLO")` returns `"Hello"`.
  2. `capitalize("")` returns `""`.
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Implement capitalize and wire eval-contract gates.
