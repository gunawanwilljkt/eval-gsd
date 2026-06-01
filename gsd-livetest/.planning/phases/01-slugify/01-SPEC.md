# Phase 1: Slugify — Specification

**Created:** 2026-06-01
**Ambiguity score:** 0.05 (gate: ≤ 0.20)
**Requirements:** 2 locked

## Goal

Add a `slugify(text)` ESM function (`src/slugify.mjs`) that converts arbitrary text to a
URL-safe slug: lowercased, trimmed, runs of non-alphanumerics collapsed to a single `-`,
with leading/trailing `-` stripped.

## Background

Nothing exists yet — `src/slugify.mjs` does not exist. This is the first phase of a new,
dependency-free Node ESM project.

## Requirements

1. **Basic slug**: `slugify("Hello World")` returns `"hello-world"`.
   - Current: function does not exist.
   - Target: lowercases and joins words with a single hyphen.
   - Acceptance: `slugify("Hello World") === "hello-world"` (REQ-01).

2. **Collapse + trim + strip**: `slugify("  A__B--C!  ")` returns `"a-b-c"`.
   - Current: function does not exist.
   - Target: collapse runs of non-alphanumerics to one `-`, trim whitespace, strip
     leading/trailing `-`, drop punctuation.
   - Acceptance: `slugify("  A__B--C!  ") === "a-b-c"` (REQ-02).

## Boundaries

**In scope:**
- A single exported `slugify(text)` function in `src/slugify.mjs` (ESM).

**Out of scope:**
- Unicode transliteration — ASCII-only target.
- Configurable separator — fixed `-`.
- CLI / packaging / publishing — library function only.

## Constraints

No dependencies. Node ESM (`.mjs`). No additional constraints beyond standard project conventions.

## Acceptance Criteria

- [ ] `slugify("Hello World") === "hello-world"`
- [ ] `slugify("  A__B--C!  ") === "a-b-c"`
